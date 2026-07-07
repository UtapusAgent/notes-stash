const meta={"name":"Notes App","slug":"notes-stash","features":["Create notes","Search notes","Delete notes","Local persistence"]};
const key="slop:"+meta.slug;
const $=(s)=>document.querySelector(s);
const state=JSON.parse(localStorage.getItem(key)||"[]");
function save(){localStorage.setItem(key,JSON.stringify(state));render();}
function add(){
  const text=$("#text").value.trim();
  if(!text)return;
  state.unshift({id:Date.now(),text,done:false,tag:$("#tag")?.value||"misc",created:new Date().toLocaleString()});
  $("#text").value="";
  save();
}
function render(){
  $("#items").innerHTML=state.map((x,i)=>`<div class="card"><div class="row"><strong class="${x.done?"done":""}">${escapeHtml(x.text)}</strong><span class="muted">${escapeHtml(x.tag||"item")}</span></div><p class="muted">${x.created||""}</p><button onclick="toggle(${i})">toggle</button> <button class="secondary" onclick="del(${i})">delete</button></div>`).join("")||"<p class='muted'>Nothing here yet.</p>";
}
function toggle(i){state[i].done=!state[i].done;save();}
function del(i){state.splice(i,1);save();}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,(c)=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));}
window.add=add;window.toggle=toggle;window.del=del;
$("#app").innerHTML=`<section class="card"><h2>${meta.name}</h2><p class="muted">${meta.features.join(" / ")}</p><div class="row"><input id="text" placeholder="Add something"><input id="tag" placeholder="tag"><button onclick="add()">Add</button></div></section><section id="items"></section>`;
render();
