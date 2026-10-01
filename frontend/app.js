const $ = (id) => document.getElementById(id);
const conversation = $('conversation');
const micBtn = $('micBtn');
const voiceTop = $('voiceTop');
const statusText = $('statusText');
const backendStatus = $('backendStatus');
const orb = $('orb');
let recognition = null;
let listening = false;

function addMessage(type, text) {
  const div = document.createElement('div');
  div.className = `msg ${type}`;
  div.innerHTML = `<small>${type === 'user' ? 'YOU' : 'RAZER AI'}</small>${escapeHtml(text)}`;
  conversation.appendChild(div);
  div.scrollIntoView({behavior:'smooth', block:'nearest'});
}
function escapeHtml(s){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function speak(text){
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = .95; u.pitch = 1;
    window.speechSynthesis.speak(u);
  }
}
function setListening(v){
  listening=v;
  micBtn.classList.toggle('listening',v);
  micBtn.querySelector('b').textContent=v?'Listening…':'Start listening';
  statusText.textContent=v?'Listening':'Ready';
  orb.style.transform=v?'scale(1.08)':'scale(1)';
}
async function sendCommand(text){
  if(!text.trim()) return;
  addMessage('user', text);
  $('heroTitle').textContent='Processing command…';
  try{
    const res=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,open_browser:false})});
    const data=await res.json();
    addMessage('ai',data.response);
    speak(data.response);
    $('heroTitle').textContent=data.success?'Command completed':'Try another command';
    if(data.url){
      setTimeout(()=>window.open(data.url,'_blank','noopener,noreferrer'),350);
    }
    if(data.action==='stop') stopListening();
    loadHistory();
  }catch(e){
    addMessage('ai','I could not reach the backend. Please start the server and try again.');
    $('heroTitle').textContent='Backend connection required';
  }
}
function startRecognition(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){addMessage('ai','Voice recognition is not supported by this browser. Please use Chrome or Edge.');return;}
  if(!recognition){
    recognition=new SR(); recognition.lang='en-US'; recognition.interimResults=false; recognition.continuous=false;
    recognition.onstart=()=>setListening(true);
    recognition.onresult=(event)=>{const text=event.results[0][0].transcript; sendCommand(text);};
    recognition.onerror=(event)=>{setListening(false);addMessage('ai',`Voice input error: ${event.error}. Please try again.`);};
    recognition.onend=()=>setListening(false);
  }
  try{recognition.start();}catch(e){}
}
function stopListening(){if(recognition){try{recognition.stop()}catch(e){}}setListening(false);}
micBtn.addEventListener('click',()=>listening?stopListening():startRecognition());
voiceTop.addEventListener('click',startRecognition);
$('clearBtn').addEventListener('click',()=>{conversation.innerHTML='';$('heroTitle').textContent='Say a command';$('heroSubtitle').textContent='Try “Hey Razer, open YouTube”';});

async function loadCommands(){
  try{
    const data=await fetch('/api/commands').then(r=>r.json());
    $('commandCount').textContent=`${data.length} commands`;
    $('commandGrid').innerHTML=data.map(c=>`<div class="command-card"><b>${escapeHtml(c.name[0].toUpperCase()+c.name.slice(1))}</b><span>${escapeHtml(c.description||'Open this website')}</span><code>“${escapeHtml(c.trigger_text)}”</code></div>`).join('');
  }catch(e){$('commandGrid').innerHTML='<div class="command-card">Backend unavailable.</div>';}
}
async function loadHistory(){
  try{
    const data=await fetch('/api/history?limit=12').then(r=>r.json());
    $('historyList').innerHTML=data.length?data.map(h=>`<div class="history-row"><span>${escapeHtml(h.user_text)}</span><span class="${h.success?'success':'failed'}">${escapeHtml(h.response)}</span><span>${escapeHtml(h.created_at)}</span></div>`).join(''):'<div class="history-row"><span>No commands yet.</span></div>';
  }catch(e){$('historyList').innerHTML='';}
}
async function checkBackend(){
  try{await fetch('/api/health');backendStatus.textContent='● Online';backendStatus.style.color='#59db99';}
  catch(e){backendStatus.textContent='● Offline';backendStatus.style.color='#ff8c9e';}
}
$('refreshHistory').addEventListener('click',loadHistory);
checkBackend();loadCommands();loadHistory();
