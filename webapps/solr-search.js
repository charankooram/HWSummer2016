/* .. start with all the global variables here...*/
var url = "http://localhost:8983/solr/feds/query?q=";
var pageArray = [];
console.log("At the beginning page set is:" + pageArray.toString());
var current = 0;
var nextCursorMarker = null;

function createRequest() {
    "use strict";
    var result = null;
    if (window.XMLHttpRequest) {
        result = new XMLHttpRequest();
    }
    return result;
}

var req = createRequest();

function GetResponse(url, cursorMarker) {
    "use strict";
    url = url + cursorMarker;
    req.open("GET", url, true);
    req.send();
    console.log("REQUEST SENT");
}

function addnewCursorMarker(newCursorMarker) {
    "use strict";
    // check if cursormarker is not seen before.
    var flag = false;
    //var i;
    /*for (i = 0; i < pageArray.length; i += 1) {
        if (pageArray[i] === newCursorMarker) {
            flag = true;
        }
    }*/
    pageArray.forEach(function checkPresense(value) {
        if (value === newCursorMarker) {
            flag = true;
        }
    });
    if (flag !== true) {
        pageArray[current + 1] = newCursorMarker;
    }
    console.log("At the beginning page after this function :" + pageArray.toString());
}



function onGettingResponse() {
    "use strict";
    console.log("Ready state is:" + req.readyState);
    console.log("Ready status:" + req.status);

    if (req.readyState === 4) {
        var Data = JSON.parse(req.responseText);
        var out = "";
        var trailingdots = "....";
        //var i;

        console.log(Data.response);
        console.log(Data.responseHeader);
        console.log(Data.nextCursorMark);
        var urlstring;
        var textmaterial;
        
        /*for (i = 0; i < Data.response.docs.length; i += 1) {
            urlstring = "http://docs.hortonworks.com/HDPDocuments" +
                    Data.response.docs[i].url;
            var textmaterial = Data.response.docs[i].text;
            out += "<a href=" + urlstring + ">" + Data.response.docs[i].title +
                    "</a><br />" + urlstring + "<br />" + "<p>" +
                    textmaterial.toString().substring(0, 400) + trailingdots +
                    "</p><br / >";
        }*/
        
        Data.response.docs.forEach(function AddToHTML(index) {
            urlstring = "http://docs.hortonworks.com/HDPDocuments" +
                         Data.response.docs[index].url;
            textmaterial = Data.response.docs[index].text;
            out += "<a href=" + urlstring + ">" + Data.response.docs[index].title +
                    "</a><br />" + urlstring + "<br />" + "<p>" +
                    textmaterial.toString().substring(0, 400) + trailingdots +
                    "</p><br / >";
        });

        nextCursorMarker = Data.nextCursorMark;
        addnewCursorMarker(nextCursorMarker);
        document.getElementById("incoming").innerHTML = out;
    }
}

req.onreadystatechange = onGettingResponse;


function UponSubmit() {
    "use strict";
    url = "http://localhost:8983/solr/feds/query?q=";
    pageArray = [];
    var textContent = document.querySelector("#q").value;
    url = url + textContent + "&sort=id+asc&cursorMark=";
    pageArray.push("*");
    new GetResponse(url, pageArray[current]);
    console.log("pageset after submitting :" + pageArray.toString());
}

function UponNext() {
    "use strict";
    if (pageArray[current + 1] === undefined) {
        console.log("cannot go next because of undefined variable");
        return;
    }
    current += 1;
    new GetResponse(url, pageArray[current]);
    console.log("pageset after hitting next :" + pageArray.toString());
}

function UponPrev() {
    "use strict";
    if (current === 0) {
        console.log("cannot go back");
        return;
    }
    current -= 1;
    new GetResponse(url, pageArray[current]);
    console.log("page set after hitting prev :" + pageArray.toString());
}
