/* .. start with all the global variables here...*/

var baseurl = "http://localhost:8983/solr/bianca/query?";
var q="";
var rows = 10;
var sort = "id+asc";
var cursorMark="";
var facet = true;
var facetfield="product"; // Initially
var pageArray = [];
console.log("At the beginning page set is:" + pageArray.toString());
var current = 0;
var nextCursorMarker = null;
var display = false;
var productComplete = null;
var releaseComplete = null;
var bkComplete = null;

window.onload = function(){
    initURL = "http://localhost:8983/solr/bianca/query?q=*:*&facet=true&facet.field=product&facet.field=release&facet.field=booktitle";
    var iproduct = document.getElementById("productGrab");
    var irelease = document.getElementById("releaseGrab");
    var ibooktitle = document.getElementById("bktitleGrab");
    productComplete = new Awesomplete(iproduct);
    releaseComplete = new Awesomplete(irelease);
    bkComplete = new Awesomplete(ibooktitle);
    GetResponse(initURL);
    
}

function createRequest() {
    "use strict";
    var result = null;
    if (window.XMLHttpRequest) {
        result = new XMLHttpRequest();
    }
    return result;
}

var req = createRequest();

function GetResponse(url) {
    "use strict";
    req.open("GET", url, true);
    req.send();
    console.log("REQUEST SENT");
}

function onGettingResponse() {
    "use strict";
    console.log("Ready state is:" + req.readyState);
    console.log("Ready status:" + req.status);

    if (req.readyState === 4) {
        var Data = JSON.parse(req.responseText);
        //var out = "";
       // var facets = "";
        //var trailingdots = "....";
        console.log(Data.response);
        console.log(Data.responseHeader);
        console.log(Data.nextCursorMark);
       // var urlstring;
       // var textmaterial;
        
       /* Data.response.docs.forEach(function AddToHTML(value) {
            console.log('The url of this file is :'+value.url);
            urlstring = "http://docs.hortonworks.com/HDPDocuments" +
                         value.url;
            textmaterial = value.text;
            if(textmaterial === undefined){
               out += "<a href=" + urlstring + ">" + value.title +
                    "</a><br />" + urlstring + "<br />" + "<p>" +
                     
                    "</p><br / >"; 
            }else{
                out += "<a href=" + urlstring + ">" + value.title +
                    "</a><br />" + urlstring + "<br />" + "<p>" +
                    textmaterial.toString().substring(0, 400) + trailingdots +
                    "</p><br / >"; 
            }
            
        }); */
        
        var out = GetIncoming(Data);
        var facets = GetFacets(Data);
        nextCursorMarker = Data.nextCursorMark;
        addnewCursorMarker(nextCursorMarker);
        if(display == true){
        document.getElementById("incoming").innerHTML = out;
        //document.getElementById("Facets").innerHTML = facets;
        }else{
            loadAutoCompletes(Data);
            display = true;
        }
    }
}

req.onreadystatechange = onGettingResponse;

function GetFacets(Data){
    var facets="";
    var index = 0;
    var index2 = 0;
    Data.facet_counts.facet_fields.product.forEach(function AddFacetsToHtml(value){
        if(index%2 === 0){
            facets = facets + "<p>"+ value + " - ";
            index2++;
        }else{
            facets = facets + value + "</p>"
        }
        index++;
    });
    return facets;
}

function GetIncoming(Data){
    var out="";
    trailingdots = "....";
    Data.response.docs.forEach(function AddIncomingToHtml(value){
        var urlstring = "http://docs.hortonworks.com/HDPDocuments"+value.url;
        textmaterial = value.text;
        if(textmaterial === undefined){
            out += "<a href=" + urlstring + ">" + value.title +
                    "</a><br />" + urlstring + "<br />" + "<p>" +
                     
                    "</p><br / >"; 
        }else{
            out += "<a href=" + urlstring + ">" + value.title +
                    "</a><br />" + urlstring + "<br />" + "<p>" +
                    textmaterial.toString().substring(0, 400) + trailingdots +
                    "</p><br / >"; 
        }
    });
    return out;
}

function UponSubmit() {
    "use strict";
    q = document.querySelector("#q").value;
    //url = url + textContent + "&sort=id+asc&cursorMark=";
    pageArray.push("*");
    cursorMark="*";
    var url = MakeUrl(baseurl,q,rows,sort,cursorMark,facet,facetfield);
    new GetResponse(url);
    //console.log("pageset after submitting :" + pageArray.toString());
    pageArray.forEach(printArray);
    document.getElementById("productGrab").disabled = false;
    document.getElementById("productGrab").placeholder="";
    
}

function UponNext() {
    "use strict";
    if (pageArray[current + 1] === undefined) {
        console.log("cannot go next because of undefined variable");
        return;
    }
    current += 1;
    cursorMark = pageArray[current];
    var url = MakeUrl(baseurl,q,rows,sort,cursorMark,facet,facetfield);
    new GetResponse(url);
    //console.log("pageset after hitting next :" + pageArray.toString());
    pageArray.forEach(printArray);
}

function UponPrev() {
    "use strict";
    if (current === 0) {
        console.log("cannot go back");
        return;
    }
    current -= 1;
    cursorMark = pageArray[current];
    var url = MakeUrl(baseurl,q,rows,sort,cursorMark,facet,facetfield);
    new GetResponse(url);
    console.log("page set after hitting prev :" + pageArray.toString());
}

function printArray(element,index,array){
     console.log('current value in the page array is :'+element);   
}

function addnewCursorMarker(newCursorMarker) {
    "use strict";
    // check if cursormarker is not seen before.
    var flag = false;
    
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

function MakeUrl(baseurl,q,rows,sort,cursorMark,facet,facetfield){
    return baseurl+"q="+q+"&rows="+rows+"&sort="+sort+"&cursorMark="+cursorMark+"&facet="+facet+"&facet.field="+facetfield;
}

function loadAutoCompletes(Data){
    var pautoarray = [];
    var rautoarray = [];
    var bautoarray = [];
    Data.facet_counts.facet_fields.product.forEach(function readproduct(element,index,array){
        if(index%2 == 0){
           pautoarray[index/2] = element; 
        }
    });
    productComplete.list = pautoarray;
    
    Data.facet_counts.facet_fields.release.forEach(function readrelease(element,index,array){
        if(index%2 == 0){
           rautoarray[index/2] = element; 
        }
    });
    releaseComplete.list = pautoarray;
    
    Data.facet_counts.facet_fields.booktitle.forEach(function readbooktitle(element,index,array){
        if(index%2 == 0){
           bautoarray[index/2] = element; 
        }
    });
    bkComplete.list = pautoarray;
}