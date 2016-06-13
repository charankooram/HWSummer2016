/* .. start with all the global variables here...*/
var url = 'http://localhost:8983/solr/feds/query?q=';
var pageArray = [];
console.log("At the beginning page set is:" + pageArray.toString());
var current = 0;
var nextCursorMarker = null;

function createRequest() {
    var result = null;
    if (window.XMLHttpRequest) {
        result = new XMLHttpRequest();
    }
    return result;
}

var req = createRequest();

function GetResponse(url, cursorMarker) {
    url = url + cursorMarker;
    req.open("GET", url, true);
    req.send();
    console.log("REQUEST SENT");
}

function addnewCursorMarker(newCursorMarker){
    // check if cursormarker is not seen before.
    var flag = false;
    var i;
    for(i=0;i<pageArray.length;i++){
        if(pageArray[i] == newCursorMarker){
            flag = true;
        }
    }
    if(flag != true){
        pageArray[current+1] = newCursorMarker;
    }
    console.log("At the beginning page after this function :" + pageArray.toString()); 
}

req.onreadystatechange = onGettingResponse;

function onGettingResponse(){
     console.log("Ready state is:" + req.readyState);
     console.log("Ready status:" + req.status);

     if (req.readyState == 4) {
         var Data = JSON.parse(req.responseText);
         var out = '';
         var trailingdots = "....";
         var i;

         console.log(Data.response);
         console.log(Data.responseHeader);
         console.log(Data.nextCursorMark);

         for (i = 0; i < Data.response.docs.length; i++) {
             var urlstring = 'http://docs.hortonworks.com/HDPDocuments' +
                 Data.response.docs[i].url;
             var textmaterial = Data.response.docs[i].text;
             out += '<a href=' + urlstring + '>' + Data.response.docs[i].title +
                 '</a><br />' + urlstring + '<br />' + '<p>'+
                 textmaterial.toString().substring(0,400) + trailingdots +'</p><br / >';
         }

         nextCursorMarker = Data.nextCursorMark;
         addnewCursorMarker(nextCursorMarker);
         document.getElementById("incoming").innerHTML = out;
     }
}



function UponSubmit() {
    var textContent = document.querySelector("#q").value;
    url = url + textContent + '&sort=id+asc&cursorMark=';
    pageArray.push('*');
    GetResponse(url,pageArray[current]);
    console.log("pageset after submitting :"+pageArray.toString());
}

function UponNext(){
    if(pageArray[current+1] == undefined){
        console.log("cannot go next because of undefined variable");
        return;
    }
    current++;
    GetResponse(url, pageArray[current]);
    console.log("pageset after hitting next :"+pageArray.toString());
}

function UponPrev(){
    if(current == 0){
        console.log("cannot go back");
        return;
    }
    current--;
    GetResponse(url,pageArray[current]);
    console.log("page set after hitting prev :"+pageArray.toString());
}
