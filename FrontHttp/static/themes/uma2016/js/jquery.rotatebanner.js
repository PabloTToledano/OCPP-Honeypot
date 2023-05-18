(function ($) {
    $(document).ready(function () {
        var changeBanner = function() {
            var id = $(this).find('input[name=id]').val();
            $(".initial-news ul.news-list li.active").fadeOut().removeClass('active');
            $(".initial-news ul.news-list li#" + id).fadeIn().addClass('active');
        };
        var nextBanner = function() {
            var current = $(".rotate-banner li.active");
            if(!current.length) {
                current = $(".rotate-banner li").eq(0);
            }
            var next = current.next('li');
            if(!next.length) {
                next = $(".rotate-banner li").eq(0);
            }
            if(next.get(0)!=current.get(0)) {
                current.fadeOut().removeClass('active');
                next.fadeIn().addClass('active');
            }
            setTimeout(nextBanner, 7000);
        };
        setTimeout(nextBanner, 7000);
    });
}(jQuery));
