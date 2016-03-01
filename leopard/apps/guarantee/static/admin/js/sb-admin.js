$(function() {
    $('#side-menu').metisMenu();

});

//Loads the correct sidebar on window load,
//collapses the sidebar on window resize.
$(function() {
    var checkeds = $('input.action-checkbox');

    $('.action-rowtoggle').change(function() {
     if(this.checked)
        for(var i=0;i<checkeds.size();i++){
            checkeds.eq(i)[0].checked = true;
        }
     else
        checkeds.removeAttr('checked');
    });

    $(window).bind("load resize", function() {
        if ($(this).width() < 768) {
            $('div.sidebar-collapse').addClass('collapse')
        } else {
            $('div.sidebar-collapse').removeClass('collapse')
        }
    })
})
