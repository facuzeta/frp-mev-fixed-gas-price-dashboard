
function fig_distribution__pools_handler(plot_id, data){
    var pool = data.points[0].hovertext
    console.log('fig_distribution__pools_handler open '+pool)
    window.open('/pool/'+pool, '_blank').focus();
}


function fig_disfig_distribution__token_in_start_arb_handler(plot_id, data){
    var pool = data.points[0].hovertext
    console.log('fig_distribution__pools_handler open '+pool)
    window.open('/token/'+pool, '_blank').focus();
}


 

function fig_disfig_distribution__tokens_arb_handler(plot_id, data){
    var pool = data.points[0].hovertext
    console.log('fig_disfig_distribution__tokens_arb_handler open '+pool)
    window.open('/token/'+pool, '_blank').focus();
}


 
