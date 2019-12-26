var operations = {

'bottom-page': function (elt) { elt.style.visibility = (vars.page === vars.topage) ? "visible" : "hidden"; },

};

for (var klass in operations) {

var y = document.getElementsByClassName(klass);

for (var j=0; j<y.length; ++j) operations[klass](y[j]);

}


