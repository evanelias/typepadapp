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
    sound  : null,
    playing: false,

    // returns "playing" or "paused"
    playOrPause: function(soundFile) {
      if (!this.sound) this.initSound(soundFile)
      return this.playing ? this.pause() : this.play()
    },

    play: function() {
      if (!this.sound) return

      this.playing = true
      this.sound.play()
      $('.baconplayer .play, .baconplayer .pause').toggle()
      return "playing"
    },

    pause: function() {
      if (!this.sound) return

      this.playing = false
      this.sound.pause()
      $('.baconplayer .play, .baconplayer .pause').toggle()
      return "paused"
    },

    initSound: function(soundFile) {
      this.sound = soundManager.createSound({
        id: 'baconplayer',
        url: soundFile,
        whileplaying: function() {
          BaconPlayer.moveProgressBar(this)
          BaconPlayer.setPositionTiming(this)
        },
        whileloading: function() {
          BaconPlayer.moveLoadingBar(this)
          BaconPlayer.setDurationTiming(this)
        },
        onload: function() {
          BaconPlayer.setDurationTiming(this, true)
        }
      })
    },

    moveProgressBar: function(sound) {
      var completed = sound.position / sound.durationEstimate
      $('.baconplayer .inner-progress').width(this.progressBar.width() * completed)
    },

    moveLoadingBar: function(sound) {
      var completed = sound.bytesLoaded / sound.bytesTotal
      $('.baconplayer .loading-progress').width(this.progressBar.width() * completed)
    },

    setPositionTiming: function(sound) {
      var time = millisecondsToTime(sound.position)
      $('.baconplayer .position').text(time)
    },

    setDurationTiming: function(sound, force) {
      if (!force && this.durationTimingTimer) return

      // only re-set this once every few seconds to avoid annoyance
      this.durationTimingTimer = setTimeout(function() {
        BaconPlayer.setDurationTiming(sound)
        BaconPlayer.durationTimingTimer = null
      }, 2000)

      var time = millisecondsToTime(sound.durationEstimate)
      $('.baconplayer .duration').text(time)
    },

    get progressBar() {
      return $('.baconplayer .progress')
    },

    setPosition: function(e) {
      var target = this.progressBar[0],
           sound = this.sound,
               x = parseInt(e.clientX)

      // play sound at this position
      var nMsecOffset = Math.floor((x-getOffX(target)-4)/(target.offsetWidth)*sound.durationEstimate)
      if (!isNaN(nMsecOffset)) nMsecOffset = Math.min(nMsecOffset, sound.duration)
      if (!isNaN(nMsecOffset)) sound.setPosition(nMsecOffset)
    },

    startDrag: function(e) {
      if (this.dragging || !this.sound) return

      this.attachDragHandlers()
      this.dragging = true
      this.pause()
      this.setPosition(e)
    },

    drag: function(e) {
      this.setPosition(e)
    },

    stopDrag: function(e) {
      this.removeDragHandlers()
      this.dragging = false
      this.setPosition(e)
      this.play()
    },

    attachDragHandlers: function() {
      $(document).bind('mousemove.baconplayer', function(e) {
        BaconPlayer.drag(e)
      })

      $(document).bind('mouseup.baconplayer', function(e) {
        BaconPlayer.stopDrag(e)
      })
    },

    removeDragHandlers: function() {
      $(document).unbind('mousemove.baconplayer')
      $(document).unbind('mouseup.baconplayer')
    }
  }

  ////
  // Utilities

  function millisecondsToTime(ms) {
    var seconds = Math.floor(ms/1000),
      minutes = Math.floor(seconds/60)
    seconds = seconds % 60
    seconds = seconds < 10 ? "0" + seconds : seconds

    return minutes + ":" + seconds
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
      BaconPlayer.startDrag(e)
    })
  })
})(jQuery);

////
// SoundManager 2 setup

soundManager.url = '/swf/'
soundManager.debugMode = false