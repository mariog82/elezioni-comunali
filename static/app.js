let user=null, DATA=null, currentList=null, mayorVotes={}, listVotes={}, prefs={};

async function api(url, options={}){
  const res=await fetch(url,{credentials:"include",headers:{"Content-Type":"application/json"},...options});
  const data=await res.json();
  if(!res.ok||data.ok===false)throw new Error(data.error||"Errore server");
  return data;
}

function enc(s){return btoa(unescape(encodeURIComponent(s))).replace(/=/g,'').replace(/\+/g,'_').replace(/\//g,'-')}
function nval(id){return Math.max(0, parseInt(document.getElementById(id)?.value || "0", 10) || 0)}
function sumObj(o){return Object.values(o).reduce((a,b)=>a+(parseInt(b||0,10)||0),0)}

async function start(){
  const token=new URLSearchParams(location.search).get("token");
  if(token){
    try{await api("/api/login",{method:"POST",body:JSON.stringify({token})});history.replaceState({},"","/")}
    catch(e){alert("QR non valido")}
  }
  try{const me=await api("/api/me");user=me.user;await showApp()}catch(e){}
}

async function login(){
  try{
    const phone=document.getElementById("phone").value.trim();
    const pin=document.getElementById("pin").value.trim();
    const d=await api("/api/login",{method:"POST",body:JSON.stringify({phone,pin})});
    user=d.user; await showApp();
  }catch(e){alert(e.message)}
}

async function logout(){await api("/api/logout",{method:"POST",body:"{}"});location.reload()}

async function showApp(){
  document.getElementById("loginBox").classList.add("hidden");
  document.getElementById("appBox").classList.remove("hidden");
  document.getElementById("userName").textContent=user.name;
  document.getElementById("userInfo").textContent=`Ruolo: ${user.role} - Sezione autorizzata: ${user.section||"tutte"}`;
  if(user.section)document.getElementById("section").value=user.section;
  if(user.role==="admin")document.getElementById("adminBtn").classList.remove("hidden");

  const cfg=await api("/api/config");
  DATA=cfg.data;
  DATA.mayors.forEach(n=>mayorVotes[n]=0);
  Object.entries(DATA.lists).forEach(([l,o])=>{
    listVotes[l]=0;
    prefs[l]={};
    o.candidates.forEach(c=>prefs[l][c]=0);
  });
  currentList=Object.keys(DATA.lists)[0];
  renderAll();
  updateValidationBox();
}

function renderAll(){renderMayors();renderTabs();renderList()}

function renderMayors(){
  const box=document.getElementById("mayorList");
  box.innerHTML="";
  DATA.mayors.forEach(n=>box.appendChild(row(n,"mayor",null)));
}

function renderTabs(){
  const tabs=document.getElementById("tabs");
  tabs.innerHTML="";
  Object.keys(DATA.lists).forEach(l=>{
    const b=document.createElement("button");
    b.className="tab"+(l===currentList?" active":"");
    b.textContent=l;
    b.onclick=()=>{currentList=l;renderTabs();renderList()};
    tabs.appendChild(b);
  });
}

function renderList(){
  const o=DATA.lists[currentList];
  const panel=document.getElementById("listPanel");
  panel.innerHTML=`<h3>${currentList} <span class="badge">${o.coalition}</span></h3>`;
  const lr=document.createElement("div");
  lr.className="row";
  lr.innerHTML=`<div class="name">Voti di lista</div><div class="votes" id="list_${enc(currentList)}">${listVotes[currentList]||0}</div>`;
  const p=document.createElement("button"); p.className="plus"; p.textContent="+"; p.onclick=()=>changeList(1);
  const m=document.createElement("button"); m.className="minus"; m.textContent="-"; m.onclick=()=>changeList(-1);
  lr.append(p,m);
  panel.appendChild(lr);
  o.candidates.forEach(c=>panel.appendChild(row(c,"pref",currentList)));
}

function row(name,type,list){
  const r=document.createElement("div"); r.className="row";
  const n=document.createElement("div"); n.className="name"; n.textContent=name;
  const v=document.createElement("div"); v.className="votes";
  v.id=type==="mayor"?`mayor_${enc(name)}`:`pref_${enc(list)}_${enc(name)}`;
  v.textContent=type==="mayor"?(mayorVotes[name]||0):(prefs[list][name]||0);
  const p=document.createElement("button"); p.className="plus"; p.textContent="+"; p.onclick=()=>changeVote(name,type,list,1);
  const m=document.createElement("button"); m.className="minus"; m.textContent="-"; m.onclick=()=>changeVote(name,type,list,-1);
  r.append(n,v,p,m);
  return r;
}

function changeList(delta){
  listVotes[currentList]=Math.max(0,(listVotes[currentList]||0)+delta);
  document.getElementById(`list_${enc(currentList)}`).textContent=listVotes[currentList];
  updateValidationBox();
}

function changeVote(name,type,list,delta){
  if(type==="mayor"){
    mayorVotes[name]=Math.max(0,(mayorVotes[name]||0)+delta);
    document.getElementById(`mayor_${enc(name)}`).textContent=mayorVotes[name];
  }else{
    prefs[list][name]=Math.max(0,(prefs[list][name]||0)+delta);
    document.getElementById(`pref_${enc(list)}_${enc(name)}`).textContent=prefs[list][name];
  }
  updateValidationBox();
}

function validVotesForControl(){
  const validMayor=sumObj(mayorVotes);
  const validList=sumObj(listVotes);
  return Math.max(validMayor, validList);
}

function expectedVoters(){
  return validVotesForControl()+nval("blankBallots")+nval("nullBallots")+nval("contestedBallots");
}

function updateValidationBox(){
  const box=document.getElementById("validationBox");
  if(!box)return;
  const voters=nval("voters");
  const valid=validVotesForControl();
  const blank=nval("blankBallots");
  const nul=nval("nullBallots");
  const contested=nval("contestedBallots");
  const expected=valid+blank+nul+contested;
  const diff=voters-expected;
  box.className="card small "+(diff===0?"ok":"warn");
  box.innerHTML=`<b>Controllo votanti:</b><br>
  Voti validi rilevati = ${valid}<br>
  Schede bianche = ${blank}, nulle = ${nul}, contestate = ${contested}<br>
  Totale calcolato = ${expected}<br>
  Votanti inseriti = ${voters}<br>
  ${diff===0 ? "<b>Quadratura corretta.</b>" : "<b>Errore di quadratura:</b> differenza " + diff + ". I votanti devono essere uguali a voti validi + bianche + nulle + contestate."}`;
}

function generateMessage(){
  const section=document.getElementById("section").value.trim()||"non indicata";
  const voters=nval("voters");
  const blank=nval("blankBallots");
  const nul=nval("nullBallots");
  const contested=nval("contestedBallots");
  const valid=validVotesForControl();
  const expected=expectedVoters();

  let txt=`RIEPILOGO VOTI - Comunali Barcellona P.G.\nSezione: ${section}\nAggiornamento: ${new Date().toLocaleString("it-IT")}\n`;
  txt+=`\nQUADRATURA SEGGIO\nVotanti: ${voters}\nVoti validi: ${valid}\nSchede bianche: ${blank}\nSchede nulle: ${nul}\nSchede contestate: ${contested}\nTotale controllo: ${expected}\nEsito: ${voters===expected?"OK":"NON QUADRA"}\n`;

  txt+=`\nCANDIDATI SINDACO\n`;
  Object.entries(mayorVotes).sort((a,b)=>b[1]-a[1]).forEach(([n,v],i)=>txt+=`${i+1}. ${n}: ${v}\n`);

  txt+=`\nLISTE\n`;
  Object.entries(listVotes).sort((a,b)=>b[1]-a[1]).forEach(([n,v],i)=>txt+=`${i+1}. ${n}: ${v}\n`);

  txt+=`\nPREFERENZE PER LISTA\n`;
  Object.keys(DATA.lists).forEach(l=>{
    txt+=`\n${l}\n`;
    Object.entries(prefs[l]).sort((a,b)=>b[1]-a[1]).filter(x=>x[1]>0).forEach(([n,v],i)=>txt+=`${i+1}. ${n}: ${v}\n`);
  });

  document.getElementById("messageBox").value=txt;
  return txt;
}

async function copyMessage(){
  const txt=generateMessage();
  await navigator.clipboard.writeText(txt);
  alert("Messaggio copiato");
}

function clearMessage(){document.getElementById("messageBox").value=""}

async function sendReport(){
  updateValidationBox();
  const voters=nval("voters");
  const expected=expectedVoters();
  if(voters!==expected){
    alert(`Impossibile inviare: il numero dei votanti non quadra. Votanti=${voters}, totale calcolato=${expected}.`);
    return;
  }
  try{
    await api("/api/report",{method:"POST",body:JSON.stringify({
      section:document.getElementById("section").value.trim(),
      voters,
      blank_ballots:nval("blankBallots"),
      null_ballots:nval("nullBallots"),
      contested_ballots:nval("contestedBallots"),
      mayors:mayorVotes,
      list_votes:listVotes,
      preferences:prefs
    })});
    alert("Dati inviati al server centrale");
  }catch(e){alert(e.message)}
}

start();