/* .. start with all the global variables here...*/
var url = 'http://localhost:8983/solr/charan06091231/query?q=';
var pageArray = [];
console.log("At the beginning page set is :"+pageArray.toString());
var current = 0;
var nextCursorMarker = null;

function createRequest(){
    var result = null;
    if(window.XMLHttpRequest){
        result = new XMLHttpRequest();
    }
    return result;    
}

var req = createRequest();

function GetResponse(url, cursorMarker){
    url = url + cursorMarker;
    req.open("GET",url,true);
    req.send();
    console.log("REQUEST SENT");
}

req.onreadystatechange = onGettingResponse; 

function onGettingResponse(){
     console.log("Ready state is :"+req.readyState);
     console.log("Ready status :"+req.status);
     if(req.readyState == 4){
         var Data = JSON.parse(req.responseText);
         var out = '';
         var trailingdots = "....";
         var i;
         console.log(Data.response);
         console.log(Data.responseHeader);
         console.log(Data.nextCursorMark);
         for(i=0;i<Data.response.docs.length;i++){
             var urlstring = 'http://docs.hortonworks.com/HDPDocuments'+Data.response.docs[i].url;
             var textmaterial = Data.response.docs[i].text;
             out += '<a href='+urlstring+'>'+Data.response.docs[i].title + '</a><br>' +
			   		urlstring + '<br>' +
				'<p>'+ textmaterial.toString().substring(0,400) + trailingdots +'</p><br>';
		
         }
         nextCursorMarker = Data.nextCursorMark;
         //if(!pageSet.has(nextCursorMarker)){
            // pageSet.add(nextCursorMarker);
         //
         var flag = true;
         for(var i=0;i<pageArray.length;i++){
             if(pageArray[i] == nextCursorMarker){
                 flag = false;
                 console.log("next page already found in the pages list");
             }
         }
         if(flag != false){
             pageArray.push(nextCursorMarker);
         }
         
         pageArray.push(nextCursorMarker);
         document.getElementById("incoming").innerHTML = out;
         
     }
}



function UponSubmit(){
    var textContent = document.querySelector("#q").value;
    url = url + textContent + '&sort=id+asc&cursorMark='
    GetResponse(url,'*');
    pageArray.push('*');
    console.log("after submit button the pageset is :"+pageArray.toString());
    current = 0;
    console.log("current is :"+current);
}

function UponNext(){
    current++;
    console.log("current is :"+current);
    console.log("current mark in the pageset :"+pageArray[current]);
    GetResponse(url,pageArray[current]);
}

function UponPrev(){
    current--;
    console.log("current is :"+current);
    GetResponse(url,pageArray[current]);
}


