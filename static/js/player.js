/* ============================================================
   Radilox mini music player
   - Single persistent <audio> element that lives outside the
     swappable #page-content region, so it survives in-site
     navigation (see soft-nav.js).
   - Real 3-band EQ (bass / mid / treble) via Web Audio
     BiquadFilterNodes — not just a visual effect.
   - A small animated visualizer driven by an AnalyserNode.
   - Media Session API so the lock screen / notification shade /
     headset buttons show title, artwork, and next/prev controls.
   - State (track, position, volume, EQ) persisted to
     sessionStorage as a best-effort resume point across full page
     loads (soft-nav makes this mostly unnecessary, but it's a
     graceful fallback for hard navigations, e.g. logging in).
   ============================================================ */
(function () {
  'use strict';

  var STORAGE_KEY = 'radilox_player_state_v1';

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function fmtTime(sec) {
    if (!isFinite(sec) || sec < 0) sec = 0;
    var m = Math.floor(sec / 60);
    var s = Math.floor(sec % 60);
    return m + ':' + (s < 10 ? '0' : '') + s;
  }

  function Player() {
    this.audio = $('#mp-audio');
    this.root = $('#mini-player');
    this.queue = [];
    this.index = -1;
    this.audioCtx = null;
    this.sourceNode = null;
    this.bassNode = null;
    this.midNode = null;
    this.trebleNode = null;
    this.analyser = null;
    this.visualizerRAF = null;
    this._graphReady = false;

    this._bindUI();
    this._bindMediaEvents();
    this._bindDelegatedTriggers();
    this._restoreState();
  }

  Player.prototype._ensureAudioGraph = function () {
    if (this._graphReady) return;
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      this.audioCtx = new Ctx();
      this.sourceNode = this.audioCtx.createMediaElementSource(this.audio);
      this.bassNode = this.audioCtx.createBiquadFilter();
      this.bassNode.type = 'lowshelf';
      this.bassNode.frequency.value = 200;
      this.midNode = this.audioCtx.createBiquadFilter();
      this.midNode.type = 'peaking';
      this.midNode.frequency.value = 1000;
      this.midNode.Q.value = 0.9;
      this.trebleNode = this.audioCtx.createBiquadFilter();
      this.trebleNode.type = 'highshelf';
      this.trebleNode.frequency.value = 4000;
      this.analyser = this.audioCtx.createAnalyser();
      this.analyser.fftSize = 64;

      this.sourceNode
        .connect(this.bassNode)
        .connect(this.midNode)
        .connect(this.trebleNode)
        .connect(this.analyser)
        .connect(this.audioCtx.destination);

      this._graphReady = true;
      this._restoreEQ();
      this._startVisualizer();
    } catch (e) {
      // Web Audio unsupported / blocked — playback still works, just
      // without EQ or the visualizer.
      console.warn('Radilox: audio graph unavailable', e);
    }
  };

  Player.prototype._bindUI = function () {
    var self = this;
    this.elPlay = $('#mp-play');
    this.elNext = $('#mp-next');
    this.elPrev = $('#mp-prev');
    this.elSeek = $('#mp-seek');
    this.elCur = $('#mp-cur-time');
    this.elDur = $('#mp-dur-time');
    this.elVol = $('#mp-volume');
    this.elTitle = $('#mp-title');
    this.elArtist = $('#mp-artist');
    this.elCover = $('#mp-cover-img');
    this.elEqToggle = $('#mp-eq-toggle');
    this.elEqPanel = $('#eq-panel');
    this.elBars = $all('.mp-eq-bar', this.root);

    if (this.elPlay) this.elPlay.addEventListener('click', function () { self.toggle(); });
    if (this.elNext) this.elNext.addEventListener('click', function () { self.next(true); });
    if (this.elPrev) this.elPrev.addEventListener('click', function () { self.prev(); });
    if (this.elSeek) this.elSeek.addEventListener('input', function () {
      if (self.audio.duration) self.audio.currentTime = (self.elSeek.value / 1000) * self.audio.duration;
    });
    if (this.elVol) this.elVol.addEventListener('input', function () {
      self.audio.volume = parseFloat(self.elVol.value);
      self._saveState();
    });
    if (this.elEqToggle) this.elEqToggle.addEventListener('click', function () {
      self.elEqPanel.classList.toggle('open');
    });
    document.addEventListener('click', function (e) {
      if (self.elEqPanel && self.elEqPanel.classList.contains('open') &&
          !self.elEqPanel.contains(e.target) && e.target !== self.elEqToggle) {
        self.elEqPanel.classList.remove('open');
      }
    });
    $all('.eq-band input[type=range]').forEach(function (input) {
      input.addEventListener('input', function () {
        self.setEQ(input.dataset.band, parseFloat(input.value));
      });
    });
  };

  Player.prototype._bindMediaEvents = function () {
    var self = this;
    this.audio.addEventListener('timeupdate', function () {
      if (!self.audio.duration) return;
      var frac = self.audio.currentTime / self.audio.duration;
      if (self.elSeek) self.elSeek.value = Math.round(frac * 1000);
      if (self.elCur) self.elCur.textContent = fmtTime(self.audio.currentTime);
      if (self.elDur) self.elDur.textContent = fmtTime(self.audio.duration);
      self._throttledSave();
    });
    this.audio.addEventListener('play', function () { self._setPlayIcon(true); self._saveState(); });
    this.audio.addEventListener('pause', function () { self._setPlayIcon(false); self._saveState(); });
    this.audio.addEventListener('ended', function () { self.next(true); });
    this.audio.addEventListener('loadedmetadata', function () {
      if (self.elDur) self.elDur.textContent = fmtTime(self.audio.duration);
    });
  };

  // Any element with class="song-trigger" and data-* fields becomes a
  // playable track. Clicking one builds a queue from every song-trigger
  // sharing its data-queue-group, in DOM order, and starts playback.
  Player.prototype._bindDelegatedTriggers = function () {
    var self = this;
    document.addEventListener('click', function (e) {
      var el = e.target.closest('.song-trigger');
      if (!el) return;
      e.preventDefault();
      var group = el.dataset.queueGroup || 'default';
      var groupEls = $all('.song-trigger[data-queue-group="' + CSS.escape(group) + '"]');
      var tracks = groupEls.map(self._trackFromEl);
      var startIndex = groupEls.indexOf(el);
      self.loadQueue(tracks, startIndex);
      self.play();
    });
  };

  Player.prototype._trackFromEl = function (el) {
    return {
      id: el.dataset.id,
      title: el.dataset.title,
      artist: el.dataset.artist,
      src: el.dataset.src,
      cover: el.dataset.cover || '',
      detailUrl: el.dataset.detail || '',
    };
  };

  Player.prototype.loadQueue = function (tracks, startIndex) {
    this.queue = tracks;
    this.index = startIndex;
    this._loadCurrent();
  };

  Player.prototype._loadCurrent = function () {
    var track = this.queue[this.index];
    if (!track) return;
    this.audio.src = track.src;
    this.audio.load();
    if (this.elTitle) this.elTitle.textContent = track.title;
    if (this.elArtist) this.elArtist.textContent = track.artist;
    if (this.elCover) {
      if (track.cover) { this.elCover.src = track.cover; this.elCover.style.display = ''; }
      else { this.elCover.removeAttribute('src'); this.elCover.style.display = 'none'; }
    }
    this.root.classList.add('visible');
    document.body.classList.add('has-player');
    this._updateMediaSession(track);
    this._saveState();
  };

  Player.prototype.play = function () {
    this._ensureAudioGraph();
    if (this.audioCtx && this.audioCtx.state === 'suspended') this.audioCtx.resume();
    var p = this.audio.play();
    if (p && p.catch) p.catch(function () { /* needs a user gesture — fine, button click already is one */ });
  };

  Player.prototype.pause = function () { this.audio.pause(); };

  Player.prototype.toggle = function () {
    if (this.audio.paused) this.play(); else this.pause();
  };

  Player.prototype.next = function (userInitiated) {
    if (this.index + 1 < this.queue.length) {
      this.index += 1;
      this._loadCurrent();
      this.play();
    } else if (userInitiated) {
      this.audio.currentTime = 0;
      this.pause();
    }
  };

  Player.prototype.prev = function () {
    if (this.audio.currentTime > 3) { this.audio.currentTime = 0; return; }
    if (this.index > 0) {
      this.index -= 1;
      this._loadCurrent();
      this.play();
    } else {
      this.audio.currentTime = 0;
    }
  };

  Player.prototype._setPlayIcon = function (playing) {
    if (!this.elPlay) return;
    this.elPlay.innerHTML = playing
      ? '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>'
      : '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';
  };

  Player.prototype.setEQ = function (band, dbValue) {
    this._ensureAudioGraph();
    if (!this._graphReady) return;
    var node = band === 'bass' ? this.bassNode : band === 'mid' ? this.midNode : this.trebleNode;
    if (node) node.gain.value = dbValue;
    this._saveState();
  };

  Player.prototype._restoreEQ = function () {
    var state = this._readState();
    if (!state || !state.eq) return;
    var self = this;
    ['bass', 'mid', 'treble'].forEach(function (band) {
      if (typeof state.eq[band] === 'number') {
        self.setEQ(band, state.eq[band]);
        var input = $('.eq-band input[data-band="' + band + '"]');
        if (input) input.value = state.eq[band];
      }
    });
  };

  Player.prototype._startVisualizer = function () {
    var self = this;
    if (!this.analyser || !this.elBars.length) return;
    var data = new Uint8Array(this.analyser.frequencyBinCount);
    function tick() {
      self.visualizerRAF = requestAnimationFrame(tick);
      if (self.audio.paused) return;
      self.analyser.getByteFrequencyData(data);
      var step = Math.floor(data.length / self.elBars.length) || 1;
      self.elBars.forEach(function (bar, i) {
        var v = data[i * step] || 0;
        bar.style.height = Math.max(15, (v / 255) * 100) + '%';
      });
    }
    tick();
  };

  Player.prototype._updateMediaSession = function (track) {
    if (!('mediaSession' in navigator)) return;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: track.title,
      artist: track.artist,
      album: 'Radilox',
      artwork: track.cover ? [
        { src: track.cover, sizes: '512x512', type: 'image/jpeg' },
      ] : [],
    });
    var self = this;
    navigator.mediaSession.setActionHandler('play', function () { self.play(); });
    navigator.mediaSession.setActionHandler('pause', function () { self.pause(); });
    navigator.mediaSession.setActionHandler('previoustrack', function () { self.prev(); });
    navigator.mediaSession.setActionHandler('nexttrack', function () { self.next(true); });
    try {
      navigator.mediaSession.setActionHandler('seekto', function (details) {
        if (details.seekTime !== undefined) self.audio.currentTime = details.seekTime;
      });
    } catch (e) { /* not all browsers support seekto */ }
  };

  Player.prototype._throttledSave = (function () {
    var last = 0;
    return function () {
      var now = Date.now();
      if (now - last < 4000) return;
      last = now;
      this._saveState();
    };
  })();

  Player.prototype._saveState = function () {
    try {
      var track = this.queue[this.index];
      var eq = { bass: 0, mid: 0, treble: 0 };
      if (this.bassNode) eq.bass = this.bassNode.gain.value;
      if (this.midNode) eq.mid = this.midNode.gain.value;
      if (this.trebleNode) eq.treble = this.trebleNode.gain.value;
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
        track: track || null,
        position: this.audio.currentTime || 0,
        volume: this.audio.volume,
        paused: this.audio.paused,
        eq: eq,
      }));
    } catch (e) { /* storage unavailable — not fatal */ }
  };

  Player.prototype._readState = function () {
    try {
      var raw = sessionStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  };

  Player.prototype._restoreState = function () {
    var state = this._readState();
    if (!state || !state.track) return;
    this.queue = [state.track];
    this.index = 0;
    this._loadCurrent();
    var self = this;
    this.audio.addEventListener('loadedmetadata', function once() {
      self.audio.currentTime = state.position || 0;
      self.audio.removeEventListener('loadedmetadata', once);
    });
    if (typeof state.volume === 'number' && this.elVol) {
      this.audio.volume = state.volume;
      this.elVol.value = state.volume;
    }
    // Never autoplay on a fresh page load without a gesture — the mini
    // player just appears, paused, ready to resume with one tap.
  };

  document.addEventListener('DOMContentLoaded', function () {
    window.radiloxPlayer = new Player();
  });
})();
