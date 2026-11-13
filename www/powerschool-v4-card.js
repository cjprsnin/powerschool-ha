/* powerschool-v4-card — Due soon strip + subject grades; roster/attendance drills */
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&','<':'<','>':'>','"':'"',"'":'&#39;'}[c]));
const LET=[[93,'A'],[90,'A-'],[87,'B+'],[83,'B'],[80,'B-'],[77,'C+'],[73,'C'],[70,'C-'],[67,'D+'],[63,'D'],[60,'D-']];
const letter=p=>{if(p==null||p===''||isNaN(Number(p)))return '\u2013';const r=Math.round(Number(p));if(isNaN(r))return '\u2013';for(const [m,l] of LET)if(r>=m)return l;return 'F';};
/** Prefer grade_percent attr; else numeric state (course sensors store % as state). */
const coursePct=(s,a)=>{
  if(!a)a={};
  if(a.grade_percent!=null&&a.grade_percent!==''&&!isNaN(parseFloat(a.grade_percent)))return parseFloat(a.grade_percent);
  if(s&&s.state!=null&&s.state!==''&&s.state!=='unknown'&&s.state!=='unavailable'){
    const ps=parseFloat(s.state);
    if(!isNaN(ps)){
      if(a.unit_of_measurement==='%'||a.grade_letter||a.grade_scale||a.section_id!=null)return ps;
    }
  }
  return null;
};
const courseLetter=(s,a,pct)=>{
  if(a&&a.grade_letter)return a.grade_letter;
  if(pct!=null)return letter(pct);
  if(s&&s.state&&isNaN(parseFloat(s.state))&&s.state!=='unknown'&&s.state!=='unavailable')return String(s.state);
  return '\u2013';
};
const PAL=[['#3d5a80','#1b2a40'],['#2d6a4f','#1a3d2e'],['#5c4d7a','#2e2644'],['#8a6a3d','#4a3820'],['#4a6fa5','#2a3d5c'],['#6b4f3a','#3a2a1e'],['#3a7a6a','#1e4038'],['#7a4a5c','#402430']];
const palette=n=>{let h=0;const s=String(n||'');for(let i=0;i<s.length;i++)h=(h*31+s.charCodeAt(i))>>>0;return PAL[h%PAL.length];};
const fdate=d=>{if(!d)return '';const x=new Date(String(d).slice(0,10)+'T12:00:00');if(isNaN(x))return String(d);const now=new Date();const t0=new Date(now.getFullYear(),now.getMonth(),now.getDate());const t1=new Date(x.getFullYear(),x.getMonth(),x.getDate());const diff=Math.round((t1-t0)/86400000);if(diff===0)return 'Today';if(diff===1)return 'Tomorrow';if(diff===-1)return 'Yesterday';return x.toLocaleDateString('en-US',{weekday:'short'});};
const scoreLabel=a=>{if(!a)return '\u2013';if(a.missing)return 'Missing';if(a.late&&a.percent==null)return 'Late';if(a.percent!=null&&!isNaN(a.percent))return Math.round(a.percent*10)/10+'%';return 'Ungraded';};

class PowerSchoolV4Card extends HTMLElement{
  constructor(){super();this.attachShadow({mode:'open'});this._view={t:'home'};this._sig='';}
  setConfig(c){this._config=Object.assign({student:'Trent'},c);this._view={t:'home'};this._sig='';}
  set hass(h){this._hass=h;const sig=this._states().map(s=>s.entity_id+s.last_updated).join('|')+'|'+this._dueKey()+'|'+this._metaKey();if(sig!==this._sig){this._sig=sig;this._render();}}
  getCardSize(){return 8;}
  static getStubConfig(){return{student:'Trent'};}

  _isCourseSensor(s){
    const a=s.attributes||{};
    if(!s.entity_id.startsWith('sensor.')||!('student' in a))return false;
    if('window_days' in a||'attendance_status' in a)return false;
    const eid=s.entity_id.toLowerCase();
    if(/due_soon|upcoming|grade_average|missing_assignments|late_assignments|ungraded_assignments|graded_assignments|assignment_count|course_count|_status$|absences$|tardies$|absent_days|tardy_days|bulletin|schedule|roster|grade_history|standards|incomplete|exempt|collected|absent_assignments/.test(eid))return false;
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

  _findSensor(re){
    if(!this._hass)return null;
    const cands=Object.values(this._hass.states).filter(s=>{
      if(!this._stuMatch(s))return false;
      return re.test(s.entity_id.toLowerCase());
    });
    return cands[0]||null;
  }

  _dueEntity(){return this._findSensor(/due_soon/);}
  _dueKey(){const d=this._dueEntity();return d?d.entity_id+d.state+d.last_updated:'';}
  _avgEntity(){return this._findSensor(/grade_average/);}
  _rosterEntity(){return this._findSensor(/class_roster/);}
  _absentEntity(){return this._findSensor(/absent_days|_absences$/);}
  _tardyEntity(){return this._findSensor(/tardy_days|_tardies$/);}
  _metaKey(){
    const parts=[];
    for(const e of [this._avgEntity(),this._rosterEntity(),this._absentEntity(),this._tardyEntity()]){
      if(e)parts.push(e.entity_id+e.state+(e.last_updated||''));
    }
    return parts.join('|');
  }

  _courses(){
    const list=this._states().map(s=>{
      const a=s.attributes||{};
      const nm=a.course||(a.friendly_name||'').replace(/^PowerSchool\s+\w+\s+/i,'')||s.entity_id;
      const p=coursePct(s,a);
      return{id:s.entity_id,name:nm,pct:p,letter:courseLetter(s,a,p),col:palette(nm),a,teacher:a.teacher||'',room:a.room||'',assignments:a.assignments||[],missing:a.missing||0,late:a.late||0,absences:a.absences||0,tardies:a.tardies||0};
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

  _avg(cs){
    const ae=this._avgEntity();
    if(ae&&ae.state!=null&&ae.state!=='unknown'&&ae.state!=='unavailable'){
      const v=parseFloat(ae.state);if(!isNaN(v))return Math.round(v*10)/10;
    }
    const n=cs.map(c=>c.pct).filter(x=>x!=null);
    return n.length?Math.round(n.reduce((a,b)=>a+b,0)/n.length*10)/10:null;
  }

  _counts(cs){
    let miss=null,late=null;
    const me=this._findSensor(/missing_assignments/);
    const le=this._findSensor(/late_assignments/);
    if(me&&me.state!=null&&!isNaN(parseInt(me.state,10)))miss=parseInt(me.state,10);
    if(le&&le.state!=null&&!isNaN(parseInt(le.state,10)))late=parseInt(le.state,10);
    if(miss==null||late==null){
      let m=0,l=0;
      cs.forEach(c=>{m+=Number(c.missing)||0;l+=Number(c.late)||0;});
      if(miss==null)miss=m;if(late==null)late=l;
    }
    return{miss,late,issues:(miss||0)+(late||0)};
  }

  _attendanceTotals(){
    const ae=this._absentEntity();
    const te=this._tardyEntity();
    let abs=null,tar=null;
    if(ae&&ae.state!=null&&!isNaN(parseFloat(ae.state)))abs=parseFloat(ae.state);
    if(te&&te.state!=null&&!isNaN(parseFloat(te.state)))tar=parseFloat(te.state);
    if(abs==null||tar==null){
      let a=0,t=0,n=0;
      this._courses().forEach(c=>{a+=Number(c.absences)||0;t+=Number(c.tardies)||0;n++;});
      if(abs==null)abs=n?a:0;
      if(tar==null)tar=n?t:0;
    }
    return{absences:abs||0,tardies:tar||0};
  }

  _rosterRows(){
    const re=this._rosterEntity();
    let rows=(re&&re.attributes&&(re.attributes.class_roster||re.attributes.roster))||[];
    if(!Array.isArray(rows)||!rows.length){
      rows=this._courses().map(c=>({course:c.name,teacher:c.teacher,room:c.room}));
    }
    return rows.filter(r=>{
      const name=String(r.course||'').toLowerCase();
      const teach=String(r.teacher||'').toLowerCase();
      if(name.includes('lunch')||name.includes('recess'))return false;
      if(teach==='staff, staff'||teach==='staff')return false;
      return true;
    });
  }

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
    const att=this._attendanceTotals();
    const due=this._dueItems();
    const dueN=this._dueEntity()?parseInt(this._dueEntity().state,10):due.length;
    const dueCount=isNaN(dueN)?due.length:dueN;

    const stats=`<div class="stats">
      <div class="st"><span class="lbl">Average</span><b class="${avg==null?'':(avg>=90?'hi':avg>=80?'mid':'lo')}">${avg==null?'\u2013':avg+'%'}</b></div>
      <div class="st tap" data-a="roster"><span class="lbl">Classes</span><b>${cs.length}</b></div>
      <div class="st tap" data-a="issues"><span class="lbl">Missing / Late</span><b>${miss}/${late}</b></div>
      <div class="st tap" data-a="attendance"><span class="lbl">Attendance</span><b>${att.absences}a ${att.tardies}t</b></div>
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

  _rosterView(){
    const rows=this._rosterRows();
    const list=rows.map(r=>`<div class="row"><div class="mid"><div class="t1">${esc(r.course||'Class')}</div><div class="t2">${esc([r.teacher,r.room?('Rm '+r.room):''].filter(Boolean).join(' \u00b7 '))}</div></div></div>`).join('')
      ||`<div class="row"><div class="mid">No roster data</div></div>`;
    return `<div class="back" data-a="back"><ha-icon icon="mdi:chevron-left"></ha-icon> Back</div>
      <div class="sec">Class roster</div><div class="list">${list}</div>`;
  }

  _issuesView(){
    const cs=this._courses();
    const items=[];
    cs.forEach(c=>{(c.assignments||[]).forEach(a=>{
      if(a.missing||(a.late&&a.percent==null)){
        items.push({course:c.name,name:a.name,due:a.due,kind:a.missing?'Missing':'Late'});
      }
    });});
    cs.forEach(c=>{(c.a.missing_homework||[]).forEach(a=>{
      items.push({course:c.name,name:a.name,due:a.due,kind:a.late?'Late':'Missing'});
    });});
    const seen=new Set();
    const uniq=items.filter(x=>{const k=x.course+'|'+x.name;if(seen.has(k))return false;seen.add(k);return true;});
    const list=uniq.map(x=>`<div class="row"><div class="mid"><div class="t1">${esc(x.name||'Assignment')}</div><div class="t2">${esc(x.course)}${x.due?' \u00b7 '+esc(fdate(x.due)):''}</div></div><div class="sc">${esc(x.kind)}</div></div>`).join('')
      ||`<div class="row"><div class="mid">No missing or late work</div></div>`;
    return `<div class="back" data-a="back"><ha-icon icon="mdi:chevron-left"></ha-icon> Back</div>
      <div class="sec">Missing / late</div><div class="list">${list}</div>`;
  }

  _attendanceView(){
    const cs=this._courses();
    const att=this._attendanceTotals();
    const header=`<div class="att-sum"><div class="st"><span class="lbl">Absences</span><b>${att.absences}</b></div><div class="st"><span class="lbl">Tardies</span><b>${att.tardies}</b></div></div>`;
    const list=cs.map(c=>`<div class="row"><div class="mid"><div class="t1">${esc(c.name)}</div></div><div class="sc">${c.absences||0} abs \u00b7 ${c.tardies||0} tar</div></div>`).join('')
      ||`<div class="row"><div class="mid">No attendance by course</div></div>`;
    return `<div class="back" data-a="back"><ha-icon icon="mdi:chevron-left"></ha-icon> Back</div>
      <div class="sec">Attendance</div>${header}<div class="list">${list}</div>`;
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
    let body=this._home();
    if(this._view.t==='course')body=this._course(this._view.id);
    else if(this._view.t==='roster')body=this._rosterView();
    else if(this._view.t==='issues')body=this._issuesView();
    else if(this._view.t==='attendance')body=this._attendanceView();

    this.shadowRoot.innerHTML=`<style>
:host{display:block}
ha-card{background:#0c0c0e;color:#ecece8;border-radius:20px;overflow:hidden;border:1px solid rgba(200,204,212,.12)}
.wrap{padding:18px 16px 20px;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
h2{margin:0;font-size:28px;font-weight:500;letter-spacing:-.02em;color:#ecece8}
.btn{background:transparent;border:none;color:#c8ccd4;cursor:pointer;padding:6px;border-radius:10px}
.btn:hover{background:rgba(255,255,255,.06)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid rgba(200,204,212,.1)}
.st{text-align:center}.st .lbl{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.06em;color:#8a8e96;margin-bottom:4px;line-height:1.2}
.st b{font-size:16px;font-weight:600;color:#ecece8}.st b.hi{color:#c4a574}.st b.mid{color:#c8ccd4}.st b.lo{color:#d4a0a0}
.st.tap{cursor:pointer;border-radius:10px;padding:4px 2px}.st.tap:hover{background:rgba(255,255,255,.05)}
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
.att-sum{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.att-sum .st{background:rgba(255,255,255,.04);border-radius:12px;padding:12px}
.empty{padding:28px;text-align:center;color:#8a8e96}
</style><ha-card><div class="wrap">${body}</div></ha-card>`;

    const btn=this.shadowRoot.querySelector('[data-a="refresh"]');
    if(btn)btn.onclick=e=>{e.stopPropagation();this._refresh();};
    this.shadowRoot.querySelectorAll('.tile[data-id]').forEach(el=>{
      el.onclick=()=>{this._view={t:'course',id:el.dataset.id};this._render();};
    });
    this.shadowRoot.querySelectorAll('[data-a="roster"]').forEach(el=>{
      el.onclick=()=>{this._view={t:'roster'};this._render();};
    });
    this.shadowRoot.querySelectorAll('[data-a="issues"]').forEach(el=>{
      el.onclick=()=>{this._view={t:'issues'};this._render();};
    });
    this.shadowRoot.querySelectorAll('[data-a="attendance"]').forEach(el=>{
      el.onclick=()=>{this._view={t:'attendance'};this._render();};
    });
    const back=this.shadowRoot.querySelector('[data-a="back"]');
    if(back)back.onclick=()=>{this._view={t:'home'};this._render();};
  }
}

if(!customElements.get('powerschool-v4-card')){
  customElements.define('powerschool-v4-card',PowerSchoolV4Card);
} else {
  try{
    const p=customElements.get('powerschool-v4-card').prototype;
    const n=PowerSchoolV4Card.prototype;
    for(const k of Object.getOwnPropertyNames(n)){if(k!=='constructor')try{p[k]=n[k];}catch(_){}}
  }catch(_){}
}
window.customCards=window.customCards||[];
if(!window.customCards.find(c=>c.type==='powerschool-v4-card')){
  window.customCards.push({type:'powerschool-v4-card',name:'PowerSchool V4 (Due soon + grades)',description:'Dark mockup-style card with due soon, roster, attendance, and subject grades',preview:true});
}
