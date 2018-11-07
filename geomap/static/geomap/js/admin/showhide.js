if (!$) {
    $ = django.jQuery;
}
$(function(){
    // for the GPON  Feed
   $('#id_gpon_feed option').each(function() {
     if ($(this).is(':selected')) {
       if (this.value) {
         $(".fieldBox.field-router").hide();
       }

      }
    });

    $('#id_gpon_feed').change(function() {
      if (this.value) {
        $(".fieldBox.field-router").hide();
      } else {
          $(".fieldBox.field-router").show();
      }
    });

    // for the Router
    $('#id_router option').each(function() {
     if ($(this).is(':selected')) {
       if (!this.value) {
         $(".fieldBox.field-r_loop").hide();
       }
      }
    });

    $('#id_router').change(function() {
      if (this.value) {
        $(".fieldBox.field-r_loop").show();
      } else {
          $(".fieldBox.field-r_loop").hide();
      }
    });

});

