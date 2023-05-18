function changeTabImageUMA(){
        path_img = path + "themes/uma/static/img/";

//        if(location.hostname.match(/des|pre/g).length > 0){
	if((/(des|pre)/g).test(location.hostname)){
		var el_color = "_blue";
	} else {
		var el_color = "";
	}

        $("#content").css("background-image","url("+path_img+"tab_login_uma"+el_color+".png)");
        $("#content").css("min-height","505px");
        $("#content").css("margin-top","30px");
        $("#content").css("background-position","25px");
        $("#content_top").css("background-image","url("+path_img+"tab_login_top_uma"+el_color+".png)");
//        $("#content_bottom").css("background-image","url("+path_img+"tab_login_bottom_uma"+el_color+".png)");
//        $("#content_middle").css("background-image","url("+path_img+"tab_login_middle_uma"+el_color+".png)");

        $("#content_middle").css("display","none");
        $("#content_middle").css("visibility","hidden");
        $("#content_bottom").css("display","none");
        $("#content_bottom").css("visibility","hidden");
        $("#status_title").css("margin-to","70px");

        $("#org_logo").css("visibility","hidden");
        $("#org_logo").css("display","none");
        $("#adas_logo").css("margin-top","12px");
        $("#adas_logo").css("margin-left","72px");
        $("#adas_logo").css("float","left");

        $("#status_title").css("font-size","18pt");
        $("#status_title").css("font-weight","normal");
        $("#status_title").css("border-bottom-color","rgb(0, 51, 102)");
        $("#status_title").css("border-bottom-style","dotted");
        $("#status_title").css("border-bottom-width","1px");
        $("#status_title").css("float","left");
        $("#status_title").css("clear","right");
        $("#el_titulo").css("margin-left","240px");

        $("#titulo_3col").css("margin-top","2px");
        
        $("#texto_titulo").css("font-size","18pt");
        $("#texto_titulo").css("font-weight","normal");

// ACAMPOS - Para que probemos nosotros y distingamos que estamos en la máquina nueva        
//if ( (substr_compare($_SERVER["REMOTE_ADDR"],"150.214.40.",0,11) === 0) || (strcmp($_SERVER["REMOTE_ADDR"],"81.40.162.111") === 0) )
	//$("#texto_titulo").css("color","red");

	$("#debug").css("padding-top","40px");
	$("#debug").css("clear","both");

	$("#content .bloque").css("margin-top","5px");
	$("#submit_ok").css("margin-top","0px");

	$("#content .bloque .error_msg").css("margin","0");
	var pagina_index = document.getElementById('texto_titulo');
	if (pagina_index !== null) {
		$("#content_bottom").css("visibility","visible");
		$("#content_bottom").css("display","block");
		$("#content_bottom").css("margin-top","-40px");
	} else {
		$("#content_bottom").css("visibility","hidden");
		$("#content_bottom").css("display","none");
	}
	var error_mostrado = document.getElementById('login_authn_error_msg');
	if (error_mostrado === null) {
		$("#content .notes_texts").css("margin-top","-40px");
	} else {
		$("#content .notes_texts").css("visibility","hidden");
		$("#content .notes_texts").css("display","none");
	}
	$("#label_user").css("text-transform","capitalize");
	$("#label_pass").css("text-transform","capitalize");

        $("#otherlogin").css("margin-bottom","20px");
        $(".wayf_button_cl").css("margin-top","6px");
}
