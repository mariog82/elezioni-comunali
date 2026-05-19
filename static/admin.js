let mayorChart=null,listChart=null,lastData=null;
let detailCharts=[];
let currentPrefTableList=null;

async function api(url, options={}){
  const res=await fetch(url,{credentials:"include",headers:{"Content-Type":"application/json"},...options});
  const data=await res.json();
  if(!res.ok||data.ok===false)throw new Error(data.error||"Errore server");
  return data;
}

async function loadDashboard(){
  try{
    const d=await api("/api/dashboard");
    lastData=d;
    prepareSettings(d);
    renderBallotSummary(d);
    draw("mayorChart",d.mayors.map(x=>x.name),d.mayors.map(x=>x.total||0),"mayor");
    draw("listChart",d.lists.map(x=>x.name),d.lists.map(x=>x.total||0),"list");

    const tb=document.getElementById("sections");
    tb.innerHTML="";
    d.sections.forEach(s=>{
      const calculated=(s.total_lists||0)+(s.blank_ballots||0)+(s.null_ballots||0);
      const ok=calculated===(s.voters||0);
      const tr=document.createElement("tr");
      tr.innerHTML=`<td>${s.section}</td><td>${s.representative}</td><td>${s.voters||0}</td><td>${s.total_lists||0}</td><td>${s.blank_ballots||0}</td><td>${s.null_ballots||0}</td><td>${s.contested_ballots||0}</td><td>${ok?"OK":"NO ("+calculated+")"}</td><td>${s.updated_at}</td>`;
      tb.appendChild(tr);
    });

    renderPrefTableTabs(d);
    renderElected(d);
    await renderDetailCharts();
    await loadUsers();
  }catch(e){
    alert(e.message+"\nAccedi come amministratore.");
    location.href="/";
  }
}

function prepareSettings(d){
  const s=d.election.settings;
  document.getElementById("totalElectors").value=s.total_electors;
  document.getElementById("totalVoters").value=s.total_voters;
  document.getElementById("councilSeats").value=s.council_seats;
  const sel=document.getElementById("winnerMayor");
  if(!sel.dataset.ready){
    d.data.mayors.forEach(m=>{
      const o=document.createElement("option");
      o.value=m; o.textContent=m; sel.appendChild(o);
    });
    sel.dataset.ready="1";
  }
  sel.value=s.winner_mayor;
  document.getElementById("mode").value=s.mode;
}

async function saveSettings(){
  try{
    await api("/api/settings",{method:"POST",body:JSON.stringify({
      total_electors:document.getElementById("totalElectors").value,
      total_voters:document.getElementById("totalVoters").value,
      council_seats:document.getElementById("councilSeats").value,
      winner_mayor:document.getElementById("winnerMayor").value,
      mode:document.getElementById("mode").value
    })});
    alert("Parametri salvati");
    await loadDashboard();
  }catch(e){alert(e.message)}
}

function renderBallotSummary(d){
  const b=d.ballot_totals||{};
  const validLists=d.lists.reduce((a,x)=>a+(x.total||0),0);
  const calculated=validLists+(b.blank_ballots||0)+(b.null_ballots||0);
  const voters=b.voters||0;
  const settingVoters=d.election.settings.total_voters||0;
  const turnout = d.election.settings.total_electors ? (settingVoters/d.election.settings.total_electors*100).toFixed(2) : "0.00";
  document.getElementById("ballotSummary").innerHTML=`
    <p><b>Elettori impostati:</b> ${d.election.settings.total_electors} &nbsp; <b>Votanti complessivi impostati:</b> ${settingVoters} &nbsp; <b>Affluenza:</b> ${turnout}%</p>
    <p><b>Votanti rilevati dalle sezioni:</b> ${voters}<br>
    <b>Voti validi lista:</b> ${validLists}<br>
    <b>Schede bianche:</b> ${b.blank_ballots||0} &nbsp; <b>Nulle:</b> ${b.null_ballots||0} &nbsp; <b>Contestate indicative:</b> ${b.contested_ballots||0}<br>
    <b>Totale controllo, senza contestate:</b> ${calculated}<br>
    <b>Quadratura sezioni:</b> ${calculated===voters ? "OK" : "NON QUADRA"}</p>`;
}

function draw(id,labels,values,kind){
  if(kind==="mayor"&&mayorChart)mayorChart.destroy();
  if(kind==="list"&&listChart)listChart.destroy();
  const chart=new Chart(document.getElementById(id),{
    type:"bar",
    data:{labels,datasets:[{data:values,label:"Voti"}]},
    options:{responsive:true,plugins:{legend:{display:false}}}
  });
  if(kind==="mayor")mayorChart=chart;else listChart=chart;
}

function renderPrefTableTabs(d){
  const tabs=document.getElementById("prefTableTabs");
  const box=document.getElementById("prefTables");
  tabs.innerHTML="";
  if(!currentPrefTableList) currentPrefTableList=Object.keys(d.data.lists)[0];

  Object.keys(d.data.lists).forEach(listName=>{
    const btn=document.createElement("button");
    btn.className="tab"+(listName===currentPrefTableList?" active":"");
    btn.textContent=listName;
    btn.onclick=()=>{currentPrefTableList=listName; renderPrefTableTabs(lastData);};
    tabs.appendChild(btn);
  });

  const listName=currentPrefTableList;
  const allCandidates=d.data.lists[listName].candidates;
  const totals={};
  d.preferences.filter(x=>x.list_name===listName).forEach(x=>totals[x.name]=x.total||0);

  const ranked=allCandidates.map((name,idx)=>({name,total:totals[name]||0,order:idx+1}))
    .sort((a,b)=>b.total-a.total || a.order-b.order);

  let html=`<div class="card"><h3>${listName}</h3><div class="tablewrap"><table><tr><th>Pos.</th><th>Candidato</th><th>Preferenze</th></tr>`;
  ranked.forEach((r,i)=>html+=`<tr><td>${i+1}</td><td>${r.name}</td><td>${r.total}</td></tr>`);
  html+="</table></div></div>";
  box.innerHTML=html;
}

function renderElected(d){
  const e=d.election;
  const s=e.settings;
  let html=`<p><b>Sindaco/coalizione vincente impostata:</b> ${s.winner_mayor}<br>
  <b>Premio di maggioranza:</b> ${e.premium_applied?"APPLICATO":"NON applicato"} ${e.premium_applied?`(${e.premium_seats} seggi)`:""}<br>
  <span class="small">Coalizione vincente: ${e.winner_pct.toFixed(2)}% delle liste ammesse. Maggior altra coalizione: ${e.other_max_pct.toFixed(2)}%.</span></p>`;

  html+=`<h3>Seggi per coalizione</h3><div class="tablewrap"><table><tr><th>Coalizione</th><th>Voti liste ammesse</th><th>Seggi</th></tr>`;
  Object.entries(e.coalition_seats).sort((a,b)=>b[1]-a[1]).forEach(([c,seats])=>html+=`<tr><td>${c}</td><td>${e.coalition_votes[c]||0}</td><td><b>${seats}</b></td></tr>`);
  html+=`</table></div>`;

  html+=`<h3>Seggi per lista e consiglieri eletti</h3><div class="tablewrap"><table><tr><th>Lista</th><th>Coalizione</th><th>Voti lista</th><th>Seggi</th><th>Eletti simulati</th></tr>`;
  Object.entries(d.data.lists).forEach(([l,obj])=>{
    const seats=e.list_seats[l]||0;
    const elected=(e.elected[l]||[]).map(x=>`<div class="elected">${x.name} (${x.votes})</div>`).join("");
    const under=(e.list_votes[l]||0)>0 && !e.admitted_lists[l] ? ` <span class="badge">sotto soglia 5%</span>`:"";
    html+=`<tr><td>${l}${under}</td><td>${obj.coalition}</td><td>${e.list_votes[l]||0}</td><td><b>${seats}</b></td><td>${elected||"<span class='muted'>Nessun seggio</span>"}</td></tr>`;
  });
  html+=`</table></div>`;

  if(e.losing_mayors.length){
    html+=`<p class="small"><b>Nota:</b> sindaci non eletti ordinati per voti: ${e.losing_mayors.map(x=>`${x.name} (${x.votes})`).join(", ")}. La proclamazione ufficiale resta di competenza degli uffici elettorali.</p>`;
  }
  document.getElementById("electedBox").innerHTML=html;
}

function destroyDetailCharts(){
  detailCharts.forEach(ch=>ch.destroy());
  detailCharts=[];
}

function showChartTab(tab){
  ["lists","mayors","prefs"].forEach(t=>{
    document.getElementById("chartTab"+cap(t)).classList.toggle("hidden", t!==tab);
    document.getElementById("tabCharts"+cap(t)).classList.toggle("active", t===tab);
  });
}

function cap(s){ return s.charAt(0).toUpperCase()+s.slice(1); }

function makeCanvasCard(title, canvasId){
  const div=document.createElement("div");
  div.className="card";
  div.innerHTML=`<h3>${title}</h3><canvas id="${canvasId}"></canvas>`;
  return div;
}

function chartOn(canvasId, labels, values, label){
  const chart=new Chart(document.getElementById(canvasId),{
    type:"bar",
    data:{labels,datasets:[{label,data:values}]},
    options:{
      responsive:true,
      plugins:{legend:{display:false}},
      scales:{x:{ticks:{autoSkip:false,maxRotation:70,minRotation:30}}}
    }
  });
  detailCharts.push(chart);
}

async function renderDetailCharts(){
  destroyDetailCharts();
  const listsBox=document.getElementById("chartTabLists");
  const mayorsBox=document.getElementById("chartTabMayors");
  const prefsBox=document.getElementById("chartTabPrefs");
  listsBox.innerHTML="";
  mayorsBox.innerHTML="";
  prefsBox.innerHTML="";

  const d=await api("/api/section-details");
  const sections=Object.keys(d.sections).sort((a,b)=>(parseInt(a)||0)-(parseInt(b)||0) || a.localeCompare(b));
  if(sections.length===0){
    listsBox.innerHTML="<p class='small'>Nessun dato di sezione disponibile.</p>";
    mayorsBox.innerHTML="<p class='small'>Nessun dato di sezione disponibile.</p>";
    prefsBox.innerHTML="<p class='small'>Nessun dato di sezione disponibile.</p>";
    return;
  }

  Object.keys(d.data.lists).forEach((listName, idx)=>{
    const canvasId=`chart_list_section_${idx}`;
    listsBox.appendChild(makeCanvasCard(listName, canvasId));
    const values=sections.map(sec=>d.sections[sec].lists[listName]||0);
    chartOn(canvasId, sections, values, "Voti lista");
  });

  d.data.mayors.forEach((mayor, idx)=>{
    const canvasId=`chart_mayor_section_${idx}`;
    mayorsBox.appendChild(makeCanvasCard(mayor, canvasId));
    const values=sections.map(sec=>d.sections[sec].mayors[mayor]||0);
    chartOn(canvasId, sections, values, "Voti sindaco");
  });

  Object.entries(d.data.lists).forEach(([listName, obj], listIdx)=>{
    const wrapper=document.createElement("div");
    wrapper.className="card";
    wrapper.innerHTML=`<h3>${listName}</h3><p class="small">Grafici dei candidati consiglieri della lista per singolo seggio.</p>`;
    prefsBox.appendChild(wrapper);

    obj.candidates.forEach((candidate, candIdx)=>{
      const canvasId=`chart_pref_${listIdx}_${candIdx}`;
      const card=makeCanvasCard(candidate, canvasId);
      wrapper.appendChild(card);
      const values=sections.map(sec=>((d.sections[sec].preferences[listName]||{})[candidate])||0);
      chartOn(canvasId, sections, values, "Preferenze");
    });
  });
}

async function loadUsers(){
  const d=await api("/api/users");
  const box=document.getElementById("users");
  box.innerHTML="";
  d.users.forEach(u=>{
    const link=`${location.origin}/?token=${u.qr_token}`;
    const div=document.createElement("div");
    div.className="card";
    div.innerHTML=`<b>${u.name}</b><br>Codice: ${u.phone}<br>Ruolo: ${u.role}<br>Sezione: ${u.section||"tutte"}<br>Stato: ${u.active?"attivo":"disattivato"}<br><label>Link QR/accesso</label><input value="${link}" readonly onclick="this.select()"><button class="secondary" onclick="toggleUser(${u.id})">${u.active?"Disattiva":"Riattiva"}</button><button class="danger" onclick="deleteUser(${u.id})">Rimuovi</button>`;
    box.appendChild(div);
  });
}

async function createUser(){
  try{
    await api("/api/users",{method:"POST",body:JSON.stringify({
      name:document.getElementById("newName").value.trim(),
      phone:document.getElementById("newPhone").value.trim(),
      pin:document.getElementById("newPin").value.trim(),
      section:document.getElementById("newSection").value.trim(),
      role:document.getElementById("newRole").value
    })});
    alert("Utente creato");
    await loadUsers();
  }catch(e){alert(e.message)}
}

async function deleteUser(id){
  if(!confirm("Rimuovere definitivamente questo rappresentante/utente?"))return;
  try{await api(`/api/users/${id}`,{method:"DELETE"});await loadUsers()}catch(e){alert(e.message)}
}

async function toggleUser(id){
  if(!confirm("Cambiare stato attivo/disattivo dell'utente?"))return;
  try{await api(`/api/users/${id}/toggle`,{method:"PATCH",body:"{}"});await loadUsers()}catch(e){alert(e.message)}
}

async function resetVotes(){
  const c=prompt("Per confermare l'azzeramento di tutti i voti scrivi: AZZERA");
  if(c!=="AZZERA")return alert("Operazione annullata");
  try{await api("/api/reset-votes",{method:"POST",body:JSON.stringify({confirm:"AZZERA"})});alert("Voti azzerati");await loadDashboard()}catch(e){alert(e.message)}
}

loadDashboard();
setInterval(loadDashboard,30000);
