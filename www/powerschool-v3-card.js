/* powerschool-v3-card — Class Overview (standalone, full) */
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&','<':'<','>':'>','"':'"',"'":'&#39;'}[c]));
const LET=[[93,'A'],[90,'A-'],[87,'B+'],[83,'B'],[80,'B-'],[77,'C+'],[73,'C'],[70,'C-'],[67,'D+'],[63,'D'],[60,'D-']];
const letter=p=>{if(p==null||isNaN(p))return '\u2013';const r=Math.round(p);for(const [m,l] of LET)if(r>=m)return l;return 'F';};
const gcls=p=>p==null?'':(p>=90?'ga':p>=80?'gb':p>=70?'gc':'gf');
const fmt=v=>v==null?'\u2013':String(Math.round(v*100)/100);
const fdate=d=>{if(!d)return '';const x=new Date(d+'T00:00:00');return isNaN(x)?d:x.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});};
const PAL=[['#7a4aa8','#3f2468'],['#3a86a8','#255a75'],['#b8562a','#8a3a17'],['#3f8a78','#2a5f52'],['#a02f57','#772045'],['#c0392b','#8f231a'],['#8f7a26','#665518'],['#4a7a34','#345a22']];
function palette(name){const n=name.toLowerCase();
 if(/english|ela\b|reading|writing/.test(n))return PAL[6];
 if(/band|music|orchestra|choir|\bart\b|drama/.test(n))return PAL[0];
 if(/social|global|history|geograph/.test(n))return PAL[1];
 if(/science|bio|chem|physics/.test(n))return PAL[2];
 if(/algebra|math|geometry|calc/.test(n))return PAL[3];
 if(/language|spanish|french|german|latin/.test(n))return PAL[4];
 if(/physical|\bpe\b|health|gym/.test(n))return PAL[5];
 let h=0;for(const c of n)h=(h*31+c.charCodeAt(0))>>>0;return PAL[h%PAL.length];}
console.info('powerschool-v3-card loaded (standalone)');
if(!customElements.get('powerschool-v3-card')){
  class PowerSchoolV3Card extends HTMLElement{
    constructor(){super();this.attachShadow({mode:'open'});this._view={t:'home'};this._trend={};this._spark={};this._trendLoaded=false;this._trendLoading=false;this._sig='';this._refreshing=false;}
    setConfig(c){if(!c||!c.student)throw new Error('PowerSchool V3: set student (e.g. Trent)');this._config=Object.assign({},c);this._view={t:'home'};this._sig='';this._trend={};this._spark={};this._trendLoaded=false;this._trendLoading=false;}
    set hass(h){this._hass=h;const sig=this._states().map(s=>s.entity_id+s.last_updated).join('|');if(sig!==this._sig){this._sig=sig;this._render();this._loadTrends();}}
    getCardSize(){return this._config&&this._config.compact?6:10;}
    static getStubConfig(){return{student:'Trent'};}
    _isCourseSensor(s){const a=s.attributes||{};return s.entity_id.startsWith('sensor.')&&('section_id' in a||'assignments' in a||'course' in a)&&('student' in a);}
    _states(){const stu=(this._config.student||'').toLowerCase();if(!this._hass)return[];return Object.values(this._hass.states).filter(s=>{if(!this._isCourseSensor(s))return false;const a=s.attributes||{};const sn=String(a.student||'').toLowerCase();return !stu||sn===stu||s.entity_id.includes(stu.replace(/\s+/g,'_'));});}
    _avg(states){const gs=states.map(s=>parseFloat(s.state)).filter(n=>!isNaN(n));return gs.length?gs.reduce((a,b)=>a+b,0)/gs.length:null;}
    async _refresh(){if(this._refreshing||!this._hass)return;this._refreshing=true;this._render();try{await this._hass.callService('powerschool','refresh',{});}catch(e){console.warn(e);}this._refreshing=false;this._trendLoaded=false;this._render();this._loadTrends();}
    async _loadTrends(){if(!this._hass||this._trendLoading||this._trendLoaded)return;this._trendLoading=true;const ids=this._states().map(s=>s.entity_id);if(!ids.length){this._trendLoaded=true;this._trendLoading=false;return;}const end=new Date();const start=new Date(end.getTime()-14*864e5);const path='history/period/'+start.toISOString()+'?filter_entity_id='+encodeURIComponent(ids.join(','))+'&minimal_response';try{const res=await this._hass.callApi('GET',path);this._trend={};this._spark={};(res||[]).forEach(series=>{if(!series||!series.length)return;const id=(series.find(p=>p.entity_id)||series[0]).entity_id;if(!id)return;const pts=series.map(p=>({t:new Date(p.last_changed||p.last_updated).getTime(),v:parseFloat(p.state)})).filter(p=>!isNaN(p.v)).sort((a,b)=>a.t-b.t);let sample=pts;if(pts.length>12){const step=Math.ceil(pts.length/12);sample=pts.filter((_,i)=>i%step===0||i===pts.length-1);}this._spark[id]=sample;if(pts.length>=2){const dif=pts[pts.length-1].v-pts[0].v;this._trend[id]=dif>0.25?'up':dif<-0.25?'down':'flat';}});}catch(e){console.warn('ps v3 trends',e);}this._trendLoaded=true;this._trendLoading=false;this._sig='';this._render();}
    _sparkSvg(pts,dir){if(!pts||pts.length<2)return '';const W=56,H=18;const vs=pts.map(p=>p.v);let min=Math.min(...vs),max=Math.max(...vs);if(max-min<0.5){min-=1;max+=1;}const step=W/(pts.length-1);const poly=pts.map((p,i)=>{const x=(i*step).toFixed(1);const y=(H-((p.v-min)/(max-min))*H).toFixed(1);return x+','+y;}).join(' ');const stroke=dir==='up'?'#4caf50':dir==='down'?'#f44336':'var(--secondary-text-color)';return `<svg class="spark" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" aria-hidden="true"><polyline fill="none" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" points="${poly}"/></svg>`;}
    _render(){
      if(!this._config)return;
      const states=this._states();
      const avg=this._avg(states);
      const student=this._config.student||'Student';
      let body='';
      if(this._view.t==='home'){
        const tiles=states.map(s=>{const a=s.attributes||{};const nm=a.course||a.friendly_name||s.entity_id;const g=parseFloat(s.state);const [c1,c2]=palette(nm);const dir=this._trend[s.entity_id];const sp=this._sparkSvg(this._spark[s.entity_id],dir);return `<div class="tile" data-id="${esc(s.entity_id)}" style="background:linear-gradient(135deg,${c1},${c2})"><div class="lg">${g==null||isNaN(g)?'\u2013':letter(g)}</div><div class="pct">${g==null||isNaN(g)?'':Math.round(g)+'%'}</div><div class="cn">${esc(nm)}</div>${sp?`<div class="spw">${sp}</div>`:''}</div>`;}).join('')||'<div class="empty">No courses found</div>';
        body=`<div class="hdr"><div><div class="h1">${esc(student)}</div><div class="h2">${avg==null?'\u2013':Math.round(avg*10)/10+'% avg'} \u00b7 ${states.length} classes</div></div><button class="btn${this._refreshing?' spin':''}" data-a="refresh" type="button"><ha-icon icon="mdi:refresh"></ha-icon></button></div><div class="grid">${tiles}</div>`;
      } else {
        const s=this._hass.states[this._view.id];const a=(s&&s.attributes)||{};const nm=a.course||a.friendly_name||this._view.id;const grade=s?parseFloat(s.state):null;const [c1,c2]=palette(nm);const asgs=a.assignments||[];
        const rows=asgs.slice(0,30).map(x=>{const miss=!!x.missing;const late=!!x.late&&x.percent==null;let score=miss?'Missing':late?'Late':(x.percent!=null?(Math.round(x.percent*10)/10)+'%':'Ungraded');return `<div class="row"><div class="mid"><div class="t1">${esc(x.name||'Assignment')}</div><div class="t2">${x.category?esc(x.category)+' \u00b7 ':''}${x.due?esc(x.due):''}</div></div><div class="sc ${gcls(x.percent)}">${score}</div></div>`;}).join('')||'<div class="row"><div class="mid">No assignments</div></div>';
        body=`<div class="back" data-a="back">\u2039 Dashboard</div><div class="hero" style="background:linear-gradient(135deg,${c1},${c2})"><div class="l">${grade==null||isNaN(grade)?'\u2013':letter(grade)}</div><div><div class="n">${esc(nm)}</div><div class="p">${grade==null||isNaN(grade)?'':Math.round(grade)+'%'}</div></div></div><div class="card">${rows}</div>`;
      }
      this.shadowRoot.innerHTML=`<style>
:host{display:block}.wrap{padding:12px}.hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}.h1{font-size:22px;font-weight:700;color:var(--primary-text-color)}.h2{font-size:13px;color:var(--secondary-text-color)}
.btn{width:36px;height:36px;border-radius:50%;border:none;background:var(--secondary-background-color);cursor:pointer;display:inline-flex;align-items:center;justify-content:center}.btn.spin ha-icon{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.tile{border-radius:16px;padding:14px;color:#fff;cursor:pointer;min-height:88px;position:relative;overflow:hidden}.tile .lg{font-size:28px;font-weight:700;line-height:1}.tile .pct{font-size:13px;opacity:.9;margin-top:4px}.tile .cn{font-size:13px;font-weight:600;margin-top:10px;opacity:.95}.tile .spw{position:absolute;right:8px;top:8px;opacity:.9}
.back{display:flex;align-items:center;gap:4px;cursor:pointer;color:var(--primary-color);font-size:16px;padding:8px 4px;margin-bottom:8px}
.hero{border-radius:16px;color:#fff;padding:18px;display:flex;align-items:center;gap:16px;margin-bottom:12px}.hero .l{font-size:56px;font-weight:600;line-height:1}.hero .n{font-size:18px;font-weight:600}.hero .p{font-size:15px;opacity:.9}
.card{background:var(--card-background-color);border-radius:16px;border:1px solid var(--divider-color);overflow:hidden}
.row{display:flex;gap:12px;padding:12px 14px;align-items:center;border-bottom:1px solid var(--divider-color)}.row:last-child{border-bottom:none}.mid{flex:1;min-width:0}.t1{font-weight:600;font-size:15px}.t2{font-size:13px;color:var(--secondary-text-color)}.sc{text-align:right;flex:none;font-weight:600}
.ga{color:#2e9e5b}.gb{color:#3a86c8}.gc{color:#d0921f}.gf{color:#c8443a}.empty{padding:28px;text-align:center;color:var(--secondary-text-color)}
</style><ha-card><div class="wrap">${body}</div></ha-card>`;
      const btn=this.shadowRoot.querySelector('[data-a="refresh"]');
      if(btn)btn.onclick=e=>{e.stopPropagation();this._refresh();};
      this.shadowRoot.querySelectorAll('.tile[data-id]').forEach(el=>{el.onclick=()=>{this._view={t:'course',id:el.dataset.id};this._render();};});
      const back=this.shadowRoot.querySelector('[data-a="back"]');
      if(back)back.onclick=()=>{this._view={t:'home'};this._render();};
    }
  }
  customElements.define('powerschool-v3-card',PowerSchoolV3Card);
}
window.customCards=window.customCards||[];
if(!window.customCards.find(c=>c.type==='powerschool-v3-card')){
  window.customCards.push({type:'powerschool-v3-card',name:'PowerSchool V3 (Class Overview)',description:'Class Overview grade tiles, assignment lists, and course drill-down',preview:true});
}
