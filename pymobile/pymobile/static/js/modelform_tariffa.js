$(document).ready(function(){
	// $(".modelform tbody.field select#id_gestore").val("tim");
<<<<<<< HEAD
	$(".modelform tbody.field select#id_gestore").each(function(){
=======
	console.log($(".modelform tbody #id_gestore"));
	$(".modelform #id_gestore").each(function(){
>>>>>>> master
		j_obj = $(this);
		// lowercase necessario perché il nome del gestore è inserito maiuscolo
		var value = j_obj.attr("value").toLowerCase();
		var form = j_obj.closest("form");
		form.find(".hidden").closest(".modelform tbody.field").hide();
		form.find("."+value).closest(".modelform tbody.field").fadeIn("slow");					
	});
	$(".modelform").on("change", "#id_gestore", function(e){
		j_obj = $(this);
		// lowercase necessario perché il nome del gestore è inserito maiuscolo
		var value = j_obj.attr("value").toLowerCase();
		var form = j_obj.closest("form");
		form.find(".hidden").closest(".modelform tbody.field").hide();
		// if (value == "edison"){
			// form.find("tbody.modelfield label[for='id_sac']").text("Provvigione S.A.C.");	
		// } else {
			// form.find("tbody.modelfield label[for='id_sac']").text("Provvigione per contratto");
		// };
		form.find("."+value).closest(".modelform tbody.field").fadeIn("slow");
	});
});