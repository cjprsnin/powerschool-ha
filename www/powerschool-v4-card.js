/* powerschool-v4-card — Due soon strip + subject grade tiles (mockup style) */
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const LET=[[93,'A'],[90,'A-'],[87,'B+'],[83,'B'],[80,'B-'],[77,'C+'],[73,'C'],[70,'C-'],[67,'D+'],[63,'D'],[60,'D-']];
const letter=p=>{if(p==null||p===''||isNaN(Number(p)))return '\u2013';const r=Math.round(Number(p));if(isNaN(r))return '\u2013';for(const [m,l] of LET)if(r>=m)return l;return 'F';};
const coursePct=(s,a)=>{if(!a)a={};if(a.grade_percent!=null&&a.grade_percent!==''&&!isNaN(parseFloat(a.grade_percent)))return parseFloat(a.grade_percent);if(s&&s.state!=null&&s.state!==''&&s.state!=='unknown'&&s.state!=='unavailable'){const ps=parseFloat(s.state);if(!isNaN(ps)&&(a.grade_letter||a.grade_percent!=null))return ps;}return null;};
const PAL=[['#3d5a80','#1b2a40'],['#2d6a4f','#1a3d2e'],['#5c4d7a','#2e2644'],['#8a6a3d','#4a3820'],['#4a6fa5','#2a3d5c'],['#6b4f3a','#3a2a1e'],['#3a7a6a','#1e4038'],['#7a4a5c','#402430']];
const palette=n=>{let h=0;const s=String(n||'');for(let i=0;i<s.length;i++)h=(h*31+s.charCodeAt(i))>>>0;return PAL[h%PAL.length];};
const fdate=d=>{if(!d)return '';const x=new Date(String(d).slice(0,10)+'T12:00:00');if(isNaN(x))return String(d);const now=new Date();const t0=new Date(now.getFullYear(),now.getMonth(),now.getDate());const t1=new Date(x.getFullYear(),x.getMonth(),x.getDate());const diff=Math.round((t1-t0)/86400000);if(diff===0)return 'Today';if(diff===1)return 'Tomorrow';if(diff===-1)return 'Yesterday';return x.toLocaleDateString('en-US',{weekday:'short'});};
const scoreLabel=a=>{if(!a)return '\u2013';if(a.missing)return 'Missing';if(a.late&&a.percent==null)return 'Late';if(a.percent!=null&&!isNaN(a.percent))return Math.round(a.percent*10)/10+'%';return 'Ungraded';};

class PowerSchoolV4Card extends HTMLElement{
  constructor(){super();this.attachShadow({mode:'open'});this._view={t:'home'};this._sig='';}
  setConfig(c){this._config=Object.assign({student:'Trent'},c);this._view={t:'home'};this._sig='';}
  set hass(h){this._hass=h;const sig=this._states().map(s=>s.entity_id+s.last_updated).join('|')+'|'+this._dueKey();if(sig!==this._sig){this._sig=sig;this._render();}}
  getCardSize(){return 8;}
  static getStubConfig(){return{student:'Trent'};}

  _isCourseSensor(s){
    const a=s.attributes||{};
    if(!s.entity_id.startsWith('sensor.')||!('student' in a))return false;
    if('window_days' in a||'attendance_status' in a)return false;
    const eid=s.entity_id.toLowerCase();
    if(/due_soon|upcoming|grade_average|missing_assignments|late_assignments|ungraded_assignments|graded_assignments|assignment_count|course_count|_status$|absences|tardies|absent_days|tardy_days|bulletin|schedule|roster|grade_history|standards|incomplete|exempt|collected|absent_assignments/.test(eid))return false;
    return ('section_id' in a)||('missing_homework' in a)||('assignment_status' in a)||Array.isArray(a.assignments);
  }

  _stuMatch(s){
    const stu=(this._config.student||'').toLowerCase();
    const a=s.attributes||{};
    const name=String(a.student||'').toLowerCase();
    const eid=s.entity_id.toLowerCase();
    const slug=stu.replace(/\s+/g,'_');
    return name===stu||name.includes(stu)||eid.includes('_'+slug+'_')||eid.includes('powerschool_'+slug);
  }

  _states(){
    if(!this._hass)return[];
    const hide=!this._config.show_empty;
    return Object.values(this._hass.states).filter(s=>{
      if(!this._isCourseSensor(s)||!this._stuMatch(s))return false;
      if(hide){
        const a=s.attributes||{};
        const p=coursePct(s,a);
        const hasAsg=Array.isArray(a.assignments)&&a.assignments.length;
        if(p==null&&!hasAsg&&!a.grade_letter)return false;
      }
      return true;
    });
  }

  _dueEntity(){
    if(!this._hass)return null;
    const stu=(this._config.student||'').toLowerCase().replace(/\s+/g,'_');
    const cands=Object.values(this._hass.states).filter(s=>{
      const eid=s.entity_id.toLowerCase();
      if(!eid.includes('due_soon'))return false;
      return this._stuMatch(s)||eid.includes(stu);
    });
    return cands[0]||null;
  }

  _dueKey(){const d=this._dueEntity();return d?d.entity_id+d.state+d.last_updated:'';}

  _courses(){
    const list=this._states().map(s=>{
      const a=s.attributes||{};
      const nm=a.course||(a.friendly_name||'').replace(/^PowerSchool\s+\w+\s+/,'')||s.entity_id;
      const p=coursePct(s,a);
      return{id:s.entity_id,name:nm,pct:p,letter:p==null?'\u2013':letter(p),col:palette(nm),a,teacher:a.teacher||'',room:a.room||'',assignments:a.assignments||[]};
    });
    if(this._config.sort==='grade')list.sort((x,y)=>(y.pct??-1)-(x.pct??-1));
    else list.sort((x,y)=>x.name.localeCompare(y.name));
    return list;
  }

  _dueItems(){
    const d=this._dueEntity();
    const raw=(d&&d.attributes&&d.attributes.assignments)||[];
    return raw.slice(0,6).map(x=>({
      name:x.name||'Assignment',
      course:x.course||x.class||'',
      due:fdate(x.due),
      score:scoreLabel(x),
    }));
  }

  _avg(cs){const n=cs.map(c=>c.pct).filter(x=>x!=null);return n.length?Math.round(n.reduce((a,b)=>a+b,0)/n.length*10)/10:null;}
  _counts(cs){let miss=0,late=0;cs.forEach(c=>{(c.assignments||[]).forEach(a=>{if(a.missing)miss++;else if(a.late&&a.percent==null)late++;});});return{miss,late};}

  async _refresh(){
    if(!this._hass||this._refreshing)return;
    this._refreshing=true;this._render();
    try{await this._hass.callService('powerschool','refresh',{});}
    catch(e){try{await this._hass.callService('homeassistant','update_entity',{entity_id:this._states().slice(0,3).map(s=>s.entity_id)});}catch(_){}}
    this._refreshing=false;this._render();
  }

  _home(){
    const cs=this._courses();
    const avg=this._avg(cs);
    const {miss,late}=this._counts(cs);
    const due=this._dueItems();
    const dueN=this._dueEntity()?parseInt(this._dueEntity().state,10):due.length;
    const dueCount=isNaN(dueN)?due.length:dueN;

    const stats=`<div class="stats">
      <div class="st"><span class="lbl">Average</span><b class="${avg==null?'':(avg>=90?'hi':avg>=80?'mid':'lo')}">${avg==null?'\u2013':avg+'%'}</b></div>
      <div class="st"><span class="lbl">Classes</span><b>${cs.length}</b></div>
      <div class="st"><span class="lbl">Missing</span><b>${miss}</b></div>
      <div class="st"><span class="lbl">Late</span><b>${late}</b></div>
    </div>`;

    const chips=due.map(x=>`<div class="chip"><div class="c">${esc(x.course||'Class')}</div><div class="n">${esc(x.name)}</div><div class="d">${esc(x.due||'')}${x.due?' \u00b7 ':''}${esc(x.score)}</div></div>`).join('')
      ||`<div class="chip empty-chip">Nothing due soon</div>`;

    const dueStrip=dueCount>0||due.length?`<div class="due">
      <div class="due-h"><span class="due-t"><ha-icon icon="mdi:clock-outline"></ha-icon> Due soon</span><span class="badge">${dueCount||due.length}</span></div>
      <div class="chips">${chips}</div>
    </div>`:'';

    const tiles=cs.map(c=>{
      const [c1,c2]=c.col;
      return `<div class="tile" data-id="${esc(c.id)}" style="background:linear-gradient(145deg,${c1},${c2})">
        <div class="t-name">${esc(c.name)}</div>
        <div class="t-letter">${esc(c.letter)}</div>
        <div class="t-pct">${c.pct!=null?Math.round(c.pct*10)/10+'%':''}</div>
      </div>`;
    }).join('')||`<div class="empty">No courses yet</div>`;

    return `<div class="top"><h2>${esc(this._config.student||'Student')}</h2>
      <button class="btn" type="button" data-a="refresh" title="Refresh"><ha-icon icon="mdi:refresh"></ha-icon></button></div>
      ${stats}${dueStrip}
      <div class="sec">Subject grades</div>
      <div class="grid">${tiles}</div>`;
  }

  _course(id){
    const c=this._courses().find(x=>x.id===id);
    if(!c)return `<div class="back" data-a="back">\u2039 Back</div><div class="empty">Course not found</div>`;
    const as=(c.assignments||[]).slice().sort((x,y)=>(y.due||'').localeCompare(x.due||''));
    const rows=as.map(x=>{
      const sc=scoreLabel(x);
      return `<div class="row"><div class="mid"><div class="t1">${esc(x.name||'Assignment')}</div><div class="t2">${x.category?esc(x.category)+' \u00b7 ':''}${esc(fdate(x.due)||x.due||'')}</div></div><div class="sc">${esc(sc)}</div></div>`;
    }).join('')||`<div class="row"><div class="mid">No assignments</div></div>`;
    const [c1,c2]=c.col;
    return `<div class="back" data-a="back"><ha-icon icon="mdi:chevron-left"></ha-icon> Back</div>
      <div class="hero" style="background:linear-gradient(145deg,${c1},${c2})"><div class="hl">${esc(c.letter)}</div>
        <div><div class="hn">${esc(c.name)}</div><div class="hp">${c.pct!=null?c.pct+'%':'\u2013'}${c.teacher?' \u00b7 '+esc(c.teacher):''}</div></div></div>
      <div class="sec">Assignments</div><div class="list">${rows}</div>`;
  }

  _render(){
    if(!this._hass||!this._config||!this.shadowRoot)return;
    const body=this._view.t==='course'?this._course(this._view.id):this._home();
    this.shadowRoot.innerHTML=`<style>
:host{display:block}
ha-card{background:#0c0c0e;color:#ecece8;border-radius:20px;overflow:hidden;border:1px solid rgba(200,204,212,.12)}
.wrap{padding:18px 16px 20px;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
h2{margin:0;font-size:28px;font-weight:500;letter-spacing:-.02em;color:#ecece8}
.btn{background:transparent;border:none;color:#c8ccd4;cursor:pointer;padding:6px;border-radius:10px}
.btn:hover{background:rgba(255,255,255,.06)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid rgba(200,204,212,.1)}
.st{text-align:center}.st .lbl{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#8a8e96;margin-bottom:4px}
.st b{font-size:18px;font-weight:600;color:#ecece8}.st b.hi{color:#c4a574}.st b.mid{color:#c8ccd4}.st b.lo{color:#d4a0a0}
.due{margin-bottom:16px}
.due-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.due-t{display:flex;align-items:center;gap:6px;font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#8a8e96}
.due-t ha-icon{--mdc-icon-size:16px;color:#c4a574}
.badge{background:rgba(196,165,116,.2);color:#c4a574;font-size:12px;font-weight:600;min-width:22px;height:22px;border-radius:11px;display:inline-flex;align-items:center;justify-content:center;padding:0 6px}
.chips{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media(max-width:380px){.chips{grid-template-columns:1fr}}
.chip{background:rgba(255,255,255,.04);border:1px solid rgba(200,204,212,.12);border-radius:14px;padding:12px 12px 10px}
.chip .c{font-size:13px;font-weight:600;color:#c4a574;margin-bottom:4px}
.chip .n{font-size:14px;font-weight:500;color:#ecece8;margin-bottom:6px;line-height:1.25}
.chip .d{font-size:12px;color:#8a8e96}
.empty-chip{color:#8a8e96;font-size:13px;text-align:center;padding:16px}
.sec{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#8a8e96;margin:4px 0 10px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.tile{border-radius:16px;padding:14px 12px 12px;min-height:96px;cursor:pointer;display:flex;flex-direction:column;justify-content:space-between;box-shadow:0 4px 16px rgba(0,0,0,.25)}
.tile:active{transform:scale(.98)}
.t-name{font-size:11px;text-transform:uppercase;letter-spacing:.06em;opacity:.85;font-weight:600}
.t-letter{font-size:36px;font-weight:600;line-height:1.05;margin:6px 0 2px}
.t-pct{font-size:13px;opacity:.85}
.back{display:flex;align-items:center;gap:4px;cursor:pointer;color:#c8ccd4;font-size:14px;margin-bottom:12px}
.hero{display:flex;gap:14px;align-items:center;border-radius:16px;padding:16px;margin-bottom:14px}
.hl{font-size:48px;font-weight:600;line-height:1}.hn{font-size:18px;font-weight:600}.hp{font-size:13px;opacity:.9;margin-top:4px}
.list{background:rgba(255,255,255,.03);border-radius:14px;border:1px solid rgba(200,204,212,.1);overflow:hidden}
.row{display:flex;gap:10px;padding:12px 14px;border-bottom:1px solid rgba(200,204,212,.08);align-items:center}
.row:last-child{border-bottom:none}.mid{flex:1;min-width:0}.t1{font-weight:600;font-size:14px}.t2{font-size:12px;color:#8a8e96;margin-top:2px}
.sc{font-size:13px;font-weight:600;color:#c8ccd4;flex:none}
.empty{padding:28px;text-align:center;color:#8a8e96}
</style><ha-card><div class="wrap">${body}</div></ha-card>`;

    const btn=this.shadowRoot.querySelector('[data-a="refresh"]');
    if(btn)btn.onclick=e=>{e.stopPropagation();this._refresh();};
    this.shadowRoot.querySelectorAll('.tile[data-id]').forEach(el=>{
      el.onclick=()=>{this._view={t:'course',id:el.dataset.id};this._render();};
    });
    const back=this.shadowRoot.querySelector('[data-a="back"]');
    if(back)back.onclick=()=>{this._view={t:'home'};this._render();};
  }
}

if(!customElements.get('powerschool-v4-card')){
  customElements.define('powerschool-v4-card',PowerSchoolV4Card);
}
window.customCards=window.customCards||[];
if(!window.customCards.find(c=>c.type==='powerschool-v4-card')){
  window.customCards.push({type:'powerschool-v4-card',name:'PowerSchool V4 (Due soon + grades)',description:'Dark mockup-style card with due soon strip and subject grade tiles',preview:true});
}
