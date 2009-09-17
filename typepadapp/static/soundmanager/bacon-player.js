/*
  //              //
  show me the bacon
     chris@ozmm.org
  //              //

  The kind of HTML we're looking for:

  <div class="baconplayer">
    <a href="{{ request.current_item.get_file_url }}" class="play">
      <img src="/img/button-play.png" alt="play"/>
    </a>

    <a href="{{ request.current_item.get_file_url }}" class="pause">
      <img src="/img/button-pause.png" alt="pause"/>
    </a>

    <div class="progress">
      <span class="timing">
        <span class="position">0:00</span> /
        <span class="duration">0:00</span>
      </span>
      <div class="loading-progress">
        <div class="inner-progress">&nbsp;</div>
      </div>
    </div>
  </div>
 */
(function($) {
  ////
  // Show me the Bacon.

  BaconPlayer = {
    // TODO make the sound an object with a soundmanager?
    sounds : {},
    durationTimingTimers: {},
    playing: {},

    // returns "playing" or "paused"
    playOrPause: function(id, soundFile) {
      if (!this.sounds[id]) this.initSound(id, soundFile);
      return this.playing[id] ? this.pause(id) : this.play(id);
    },

    play: function(id) {
      if (!this.sounds[id]) return;

      // pause any other audio files
      $.each(this.playing, function(i) {
        if (this == true) BaconPlayer.pause(i);
      });
      this.playing[id] = true;
      this.sounds[id].play();
      this.playPauseButtons(id).toggle();
      return "playing";
    },

    pause: function(id) {
      if (!this.sounds[id]) return;

      this.playing[id] = false;
      this.sounds[id].pause();
      this.playPauseButtons(id).toggle();
      return "paused";
    },

    initSound: function(id, soundFile) {
      this.sounds[id] = soundManager.createSound({
        id: id,
        url: soundFile,
        whileplaying: function() {
          BaconPlayer.moveProgressBar(this);
          BaconPlayer.setPositionTiming(this);
        },
        whileloading: function() {
          BaconPlayer.moveLoadingBar(this);
          BaconPlayer.setDurationTiming(this);
        },
        onload: function() {
          BaconPlayer.setDurationTiming(this, true);
        }
      });
      this.playing[id] = false;
    },

    moveProgressBar: function(sound) {
      var completed = sound.position / sound.durationEstimate;
      $('#' + sound.sID + ' .inner-progress').width(this.progressBar(sound.sID).width() * completed);
    },

    moveLoadingBar: function(sound) {
      var completed = sound.bytesLoaded / sound.bytesTotal;
      $('#' + sound.sID + ' .loading-progress').width(this.progressBar(sound.sID).width() * completed);
    },

    setPositionTiming: function(sound) {
      var time = millisecondsToTime(sound.position);
      $('#' + sound.sID + ' .position').text(time);
    },

    setDurationTiming: function(sound, force) {
      if (!force && this.durationTimingTimers[sound.sID]) return;

      // only re-set this once every few seconds to avoid annoyance
      this.durationTimingTimers[sound.sID] = setTimeout(function() {
        BaconPlayer.setDurationTiming(sound);
        BaconPlayer.durationTimingTimers[sound.sID] = null;
      }, 2000);

      var time = millisecondsToTime(sound.durationEstimate);
      $('#' + sound.sID + ' .duration').text(time);
    },

    setPosition: function(id, e) {

      var target = this.progressBar(id)[0],
           sound = this.sounds[id],
               x = parseInt(e.clientX);

      // play sound at this position
      var nMsecOffset = Math.floor((x-getOffX(target)-4)/(target.offsetWidth)*sound.durationEstimate);
      if (!isNaN(nMsecOffset)) nMsecOffset = Math.min(nMsecOffset, sound.duration);
      if (!isNaN(nMsecOffset)) sound.setPosition(nMsecOffset);
    },

    startDrag: function(e) {
      id = $(e.currentTarget).parent().attr('id');

      if (this.dragging || !this.sounds[id]) return;

      this.attachDragHandlers();
      this.dragging = id; // track dragged sound id
      this.pause(id);
      this.setPosition(id, e);
    },

    drag: function(e) {
      this.setPosition(this.dragging, e);
    },

    stopDrag: function(e) {
      id = this.dragging;
      this.removeDragHandlers();
      this.dragging = null;
      this.setPosition(id, e);
      this.play(id);
    },

    attachDragHandlers: function() {
      $(document).bind('mousemove.baconplayer', function(e) {
        BaconPlayer.drag(e);
      });

      $(document).bind('mouseup.baconplayer', function(e) {
        BaconPlayer.stopDrag(e);
      });
    },

    removeDragHandlers: function() {
      $(document).unbind('mousemove.baconplayer');
      $(document).unbind('mouseup.baconplayer');
    },
    
    playPauseButtons: function(id) {
      return $('#' + id + ' .play, #' + id + ' .pause');
    },
    
    progressBar: function(id) {
      return $('#' + id + ' .progress');
    }
  }

  ////
  // Utilities

  function millisecondsToTime(ms) {
    var seconds = Math.floor(ms/1000),
      minutes = Math.floor(seconds/60);
    seconds = seconds % 60;
    seconds = seconds < 10 ? "0" + seconds : seconds;

    return minutes + ":" + seconds;
  }

  function getOffX(o) {
    // http://www.xs4all.nl/~ppk/js/findpos.html
    var curleft = 0;
    if (o.offsetParent) {
      while (o.offsetParent) {
        curleft += o.offsetLeft;
        o = o.offsetParent;
      }
    }
    else if (o.x) curleft += o.x;
    return curleft;
  }

  ////
  // Handlers

  $(function() {
    /*$('.baconplayer .play, .baconplayer .pause').click(function() {
      BaconPlayer.playOrPause(this.href)
      return false
    })*/

    $('.baconplayer .progress').mousedown(function(e) {
      BaconPlayer.startDrag(e);
    });
  })
})(jQuery);

////
// SoundManager 2 setup

soundManager.url = '/swf/';
soundManager.debugMode = false;
