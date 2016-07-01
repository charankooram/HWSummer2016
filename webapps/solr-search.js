/* .. start with all the global variables here...*/

var baseurl = "http://localhost:8983/solr/corehw/query?";
var q="";
var cursorMark="";
var facet = true;
var facetfield=""; // Initially.
var pageArray = [];
console.log("At the beginning page set is:" + pageArray.toString());
console.log("Check Updates...");
var current = 0;
var nextCursorMarker = null;
var fq1 = null;
var fq2 = null;
var fq3 = null;
var display = false; // For the initURL call to grab facets but not display *:* content.
var productComplete = null;
var releaseComplete = null;
var bkComplete = null;

/*
 * Initialize variables for the autocomplete feature once the page loads.
 * Call the initial URL to grab the facet details for product/release/booktitle.
 */
window.onload = function(){
    initURL = "http://localhost:8983/solr/corehw/query";    //?q=*:*&facet=true&facet.field=product&facet.field=release&facet.field=booktitle";
    var iproduct = document.getElementById("productGrab");
    var irelease = document.getElementById("releaseGrab");
    var ibooktitle = document.getElementById("bktitleGrab");
    productComplete = new Awesomplete(iproduct);
    productComplete.minChars = 1;
    releaseComplete = new Awesomplete(irelease);
    releaseComplete.minChars = 1;
    bkComplete = new Awesomplete(ibooktitle);
    bkComplete.minChars = 1;
    GetResponse(initURL);
}

/*
 * Create XmlHttpObject.
 * TODO: add changes from workboard.js
 */
function createRequest() {
    "use strict";
    var result = null;
    if (window.XMLHttpRequest) {
        result = new XMLHttpRequest();
    }
    return result;
}

var req = createRequest();

/*
 * Send http request to the solr URL generated.
 */
function GetResponse(url) {
    "use strict";
    req.open("GET", url, true);
    req.send();
    console.log("REQUEST SENT");
}

/*
 * If display flag is false (page just loaded) ; Read facet information for autocomplete features and update display flag.
 * Make JSON object from the response received and call parsing functions.
 * ->GetIncoming for reading the search results.
 * -> GetFacets for reading the facet tags.
 * Read cursormarker and check if the pagearray needs to be updated.
 */
function onGettingResponse() {
    "use strict";
    console.log("Ready state is:" + req.readyState);
    console.log("Ready status:" + req.status);
    if (req.readyState === 4) {
        var Data = JSON.parse(req.responseText);
        console.log(Data.response);
        console.log(Data.responseHeader);
        console.log(Data.nextCursorMark);
        var out = GetIncoming(Data);
        if(facet!=false) var facets = GetFacets(Data);
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

/*
 * Parse Json object and read facets tag from response.
 */
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

/*
 * Parse json object and read data tag from response.
 * read highlighting tag for text snippet.
 */
function GetIncoming(Data){
    var out="";
    trailingdots = "\u2026";
    Data.response.docs.forEach(function AddIncomingToHtml(value){
        var urlstring = "http://docs.hortonworks.com/HDPDocuments"+value.url;
        textmaterial = value.text;
        var i_id = value.id;
        var highlightedText = Data.highlighting[i_id].text;
        if(textmaterial === undefined){
            out += "<a href=" + urlstring + ">" + value.title +
                    "</a><br />" + urlstring + "<br />"  +
                    "<font size=1 color=blue>["+value.product+"/"+value.release+"/"+value.booktitle+"]</font>" +
                    "<br / >"; 
        }else{
            out += "<a href=" + urlstring + ">" + value.title +
                    "</a><br />" + urlstring + "<br />" +
                    "<font size=1 color=blue>["+value.product+"/"+value.release+"/"+value.booktitle+"]</font>" +
                    "<br />"+ 
                     trailingdots+" "+highlightedText +" "+ trailingdots +
                    "<br / ><br />"; 
        }
    });
    return out;
}

 /*
 * Grabs the query text and performs a search.
 * Should it clear the pagearray before pushing the * ???
 * Clears all the filter textfields.
 * Hence set all the filter query parameters to null.
 * Turn off facet.
 */
function UponSubmit() {
    "use strict";
    document.getElementById("productGrab").placeholder="product...";
    document.getElementById("releaseGrab").placeholder="release...";
    document.getElementById("bktitleGrab").placeholder="booktitle...";
    q = document.querySelector("#q").value; // Grab the query text...
    fq1 = null;
    fq2 = null;
    fq3 = null;
    pageArray.push("*");
    cursorMark="*";
    facet = false;
    var url = MakeUrl(baseurl,q,cursorMark,facet,fq1,fq2,fq3); // Since facet is false; All the remaining facetparameters are irrelavant;
    new GetResponse(url);
    pageArray.forEach(printArray);
    
}

/*
 * Increment the pagearray pointer and grab the next cursormarker to move to next page.
 * Generate Solr URL and make a http call.
 */
function UponNext() {
    "use strict";
    if (pageArray[current + 1] === undefined) {
        console.log("cannot go next because of undefined variable");
        return;
    }
    current += 1;
    cursorMark = pageArray[current];
    var url = MakeUrl(baseurl,q,cursorMark,facet,fq1,fq2,fq3);
    new GetResponse(url);
    pageArray.forEach(printArray);
}

/*
 * Decrement the pagearray pointer and grab the appropriate cursormarker to prev page.
 * Generate Solr URL and make a http call.
 */
function UponPrev() {
    "use strict";
    if (current === 0) {
        console.log("cannot go back");
        return;
    }
    current -= 1;
    cursorMark = pageArray[current];
    var url = MakeUrl(baseurl,q,cursorMark,facet,fq1,fq2,fq3);
    new GetResponse(url);
    console.log("page set after hitting prev :" + pageArray.toString());
}

/*
 * Check what filters are active from the user.
 * set those appropriate filter queries to those values grabbed
 * Make another URL.
 * Send Request.
 */
function UponFilter(){
   /* The order of the facets is always consistent : Product -> Release -> BookTitle */
    var productGrabbed = document.getElementById("productGrab").value;
    var releaseGrabbed = document.getElementById("releaseGrab").value;
    var bktitleGrabbed = document.getElementById("bktitleGrab").value;
    
    if(productGrabbed != ''){
        fq1 = productGrabbed;
    }else{
        fq1 = null;
    }
    
    if(releaseGrabbed != ''){
        fq2 = releaseGrabbed;
    }else{
        fq2 = null;
    }
    
    if(bktitleGrabbed != ''){
        fq3 = bktitleGrabbed;
    }else{
        fq3 = null;
    }
    var urlToUse = MakeUrl(baseurl,q,cursorMark,facet,fq1,fq2,fq3);
    GetResponse(urlToUse);
}

/*
 * Debugging Utility Function to print the pagenumber carrying array.
 */
function printArray(element,index,array){
     console.log('current value in the page array is :'+element);   
}

/*
 * Check if the cursormarker is not already present.
 * Update pagearray with new cursormarker.
 */
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

/*
 * Append the parameters to generate new Solr URL.
 */
function MakeUrl(baseurl,q,cursorMark,facet,fq1,fq2,fq3){
    var url = baseurl+"q="+q+"&cursorMark="+cursorMark+"&facet="+facet;
    if(fq1 != null){
        url = url + "&fq=product:"+fq1;
    }
    if(fq2 != null){
        url = url + "&fq=release:"+fq2;
    }
    if(fq3 != null){
        url = url + "&fq=booktitle:"+fq3;
    }
    return url;
   
}

/*
 * Assign autocorrect variables with facet data from response.
 */
function loadAutoCompletes(Data){
    var pautoarray = [];
    var rautoarray = [];
    var bautoarray = [];
    
    //facet array is interspersed with product name and count of the product.
    Data.facet_counts.facet_fields.product.forEach(function readproduct(element,index,array){
        if(index%2 == 0){
           pautoarray[index/2] = element; 
        }
    });
    productComplete.list = pautoarray;
    
    //facet array is interspersed with release name and count of the release.
    Data.facet_counts.facet_fields.release.forEach(function readrelease(element,index,array){
        if(index%2 == 0){
           rautoarray[index/2] = element; 
        }
    });
    releaseComplete.list = rautoarray;
    
    //facet array is interspersed with booktitle and count of the booktitle.
    Data.facet_counts.facet_fields.booktitle.forEach(function readbooktitle(element,index,array){
        if(index%2 == 0){
           bautoarray[index/2] = element; 
        }
    });
    bkComplete.list = bautoarray;
}

