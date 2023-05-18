// Google Maps API should be loaded before this
/*jslint bitwise: true, browser: true, eqeqeq: true, immed: true, newcap: true, nomen: true, plusplus: true, regexp: true, white: true, indent: 4, onevar: false */
/*global google, G_DEFAULT_ICON, G_GEO_UNKNOWN_ADDRESS, ClusterMarker, console, jQuery */
(function ($) {

    var debug = function (msg) {
        if (typeof console != "undefined" && false ) { // remove '&& false' to get some debugging info
            console.debug(msg);
        }
    };    

    $.fn.gmap = function (options) {

        var opts = $.extend({}, $.fn.gmap.defaults, options);
        return this.each(function () {
                // initialize state
                var self = this;
                var map = null;
                var cluster = {};
                var markers = {};
                var latlngmarkers = {};


                map = new google.maps.Map(this);
                $(this).data("map", map);

                
              
            }); // End of each
        
    }; // End of map

    $.fn.gmap.defaults = {
        map_type: null,
        zoom: 5,
        enable_scroll_wheel_zoom: true,
        use_small_controls: false,
        plus_icon_image: "",
        show_directions: true,
        panorama_slide_trigger: ".toStreet",
        panorama_container_selector: ".panoramasection",
        panorama_id: "panorama",
        directions_form_selector: ".googlemap-directions-form",
        directions_area_selector: ".googlemap-directions",
        directions_sidebar_selector: ".googlemap-sidebar",
        colorify_areas: false,
        filters_selector: "div.mapFilters input.mapFilter",
        alternative_filter_url: "div.mapFilters span.filterurl",
        progress_feedback_selector: "span.progressFeedback",
        filter_url: null,
        content_type_id: null,
        content_id: null,
        force_cluster_in_max_zoom: false,
        recalculate_marks_when_map_changes: false
    };

}(jQuery));
