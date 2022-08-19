$(document).ready(function() {
    (function($) {

        $.fn.fc = function(animateIn, animateOut, delay) {
            $(".fc-card").hide();
            $("#fc-home").hide();
            $("#fc-back").hide();
            $("#fc-main").show();

            var history = ["#fc-main"];

            if (!delay || delay < 0) {
                delay = 500;
            }

            $(".fc-btn").click(function() {
                var parent = $(this).parent();
                $(".fc-btn").attr("disabled", "true"); //prevent multiple clicks
                parent.removeClass(animateIn).addClass(animateOut);
                var nextId = "#C" + $(this).attr("id").substring(1);
                history.push(nextId);

                setTimeout(function() {
                    parent.hide();
                    $(nextId).addClass(animateIn).show();
                    $(".fc-btn").removeAttr("disabled");
                    $("#fc-home").show();
                    $("#fc-back").show();
                }, delay);
            });

            $("#fc-home").click(function() {
                $("#fc-home").hide();
                $("#fc-back").hide();
                history = ["#fc-main"];
                $(".fc-card").addClass(animateOut);
                setTimeout(function() {
                    $(".fc-card").hide();
                    $("#fc-main").show();
                    $(".fc-card").removeClass(animateOut).addClass(animateIn);
                }, delay);
            })

            $("#fc-back").click(function() {
                history.pop();
                $(".fc-card").addClass(animateOut);
                setTimeout(function() {
                    $(".fc-card").hide();
                    if (history.length > 1) {
                        $(history[history.length - 1]).show();
                    } else {
                        $("#fc-main").show();
                        $("#fc-home").hide();
                        $("#fc-back").hide();
                        history = ["#fc-main"];
                    }
                    $(".fc-card").removeClass(animateOut).addClass(animateIn);
                }, delay);
            })
        }
    }(jQuery));
    var contrast = false;
    $("body").fc("fadeIn", "fadeOut", 600);
    $("#language").click(function() {
        if ($("#text-language").css("display") == "none")
            $("#text-language").show();
        else
            $("#text-language").hide();

    });
  
    $("#keyboard").click(function() {
        if ($("#text-keyboard").css("display") == "none")
            $("#text-keyboard").show();
        else
            $("#text-keyboard").hide();

    })
    $("#contrast").click(toggleContrast);

    function toggleContrast() {
        if (!contrast) {
            contrast = true;
            $("body").css({
                'background': 'black'
            });
            $(".fc-card").css({
                'color': '#FFDA00'
            });
            $(".fc-btn").css({
                'background': '#FFDA00',
                'color': 'black'
            });
            $(".endpt").css({
                'background': '#FFDA00',
                'color': 'black'
            });
            $("nav").css({
                'background': '#FFDA00'
            });
            $(".navbutton").css({
                'color': 'black'
            });
            $("hr").css({
                'border-color': '#FFDA00'
            });
            $("select").css({
                'background': '#FFDA00',
                'color': 'black'
            });
        } else {
            contrast = false;
            $("body").css({
                'background': '#00b8d4'
            });
            $(".fc-card").css({
                'color': 'white'
            });
            $(".fc-btn").css({
                'background': '#0097a7',
                'color': 'white'
            });
            $(".endpt").css({
                'background': '#0097a7',
                'color': 'white'
            });
            $("nav").css({
                'background': '#009aad'
            });
            $(".navbutton").css({
                'color': '#b2ebf2'
            });
            $("hr").css({
                'border-color': '#0097a7'
            });
            $("select").css({
                'background': '#0097a7',
                'color': '#b2ebf2'
            });
        }
    }
})
