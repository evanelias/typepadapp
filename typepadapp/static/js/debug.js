jQuery(function($) {
    $.potionDebug = function(data, klass) {
        $.potionDebug.init();
    }
    $.extend($.potionDebug, {
        init: function() {
            $('#debug-close').click(function() {
                $(document).trigger('close.potionDebug');
                return false;
            });
            $('#debug-summary').click(function() {
                $('#debug-details').toggle();
                if($('#debug-details').is(':visible')) {
                    $('#debug-toolbar').addClass('visible')
                } else {
                    $('#debug-toolbar').removeClass('visible')
                }
                return false;
            });
            $('#debug-toolbar .debug-request-summary').click(function() {
                $(this).parent().children('.debug-subrequests').toggle();
                return false;
            });
            $('#debug-toolbar a.subrequest-display-payload').click(function() {
                $(this).parent().parent().children('.debug-subrequest-body').toggle();
                return false;
            });
            $('#debug-toolbar a.subrequest-display-stacktrace').click(function() {
                $(this).parent().parent().children('.debug-subrequest-stacktrace').toggle();
                return false;
            });
        },
        close: function() {
            $(document).trigger('close.potionDebug');
            return false;
        },
    });
    $(document).bind('close.potionDebug', function() {
        $('#debug-toolbar').remove()
    });
});
jQuery(function() {
    jQuery.potionDebug();
});