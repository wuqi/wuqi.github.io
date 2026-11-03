/**
 * 
 */
$(function(){
	$('.set-view-mode').click(function(){
		setReadMode($(this).data('mode'));
	});
	window.onload = function(){
		setReadMode();
	};
	
	$(window).bind("scroll", backToTopFun);
	
	$('.back-to-top').click(function() {
        $("html, body").animate({ scrollTop: 0 }, 120);
        return false;
	});
	
	$('.dropdown-toggle').click(function(){
		var target = $(this).data('target');
		console.log(target);
		if($(target).hasClass('active')){
			$(target).removeClass('active')
		}else{
			$(target).addClass('active')
		}
		return false;
	});
	
	$(document).bind('click',function(){
		$('.dropdown-menu.active').removeClass('active');
	});
	if(window.isArchive){
		$(window).bind("scroll");
	}
	backToTopFun();
});
function backToTopFun() {
    var st = $(document).scrollTop(), winh = $(window).height(),backToTopEle = $('.back-to-top');
    (st > 120)? backToTopEle.show(): backToTopEle.hide();
    //IE6下的定位
    if (!window.XMLHttpRequest) {
        backToTopEle.css("top", st + winh - 166);
    }
};

function setReadMode(mode){
	var btn = $('.set-view-mode');
	mode = mode===undefined ? getCookie('read-mode') : mode;
	//console.log(mode);
    if(mode=='day'){
    	$('body').addClass('night-mode');
    	btn.data('mode','night').find('i').attr('class','fa fa-sun-o');
    }else{
	    if($('body').hasClass('night-mode')){
	    	$('body').removeClass('night-mode');
			btn.data('mode','day').find('i').attr('class','fa fa-moon-o');
		}
	}
    setCookie('read-mode',mode,86400);
}
function setCookie(name,value,expires){  
    expires = new Date(+new Date + 1000 * 60 * 60 * 24 * expires);
    expires = ';expires=' + expires.toGMTString();
    path = ';path=/';
    document.cookie = name+"="+escape(value)+expires+path;   //转码并赋值
}
function getCookie(name) { 
	var nameEQ = name + "=";    
	var ca = document.cookie.split(';');//把cookie分割成组    
	for(var i=0;i < ca.length;i++) {    
		var c = ca[i];//取得字符串    
		while (c.charAt(0)==' ') {//判断一下字符串有没有前导空格    
			c = c.substring(1,c.length);//有的话，从第二位开始取    
		}    
		if (c.indexOf(nameEQ) == 0) {//如果含有我们要的name    
			return unescape(c.substring(nameEQ.length,c.length));//解码并截取我们要值    
		}    
	}    
	return false;
}
function delCookie(name){  
	setCookie(name,'',-1);
}
/* donate lightbox */
$(function(){
	$('#donate-btn').click(function(){
		$('#donate-lightbox').addClass('active');
		return false;
	});
	$('#donate-lightbox').click(function(){
		$(this).removeClass('active');
	});
	$('.donate-lightbox-content').click(function(e){
		e.stopPropagation();
	});
});
