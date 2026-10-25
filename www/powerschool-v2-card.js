/* powerschool-v2-card — app-style with 14d grade sparklines + trends */
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
console.info('powerschool-v2-card loaded (sparklines)');
if(!customElements.get('powerschool-v2-card')){
  class PowerSchoolV2Card extends HTMLElement{
    constructor(){super();this.attachShadow({mode:'open'});this._view={t:'home'};this._trend={};this._spark={};this._trendLoaded=false;this._trendLoading=false;this._sig='';this._refreshing=false;}
    setConfig(c){this._config=Object.assign({},c);this._view={t:'home'};this._sig='';this._trend={};this._spark={};this._trendLoaded=false;this._trendLoading=false;}
    set hass(h){this._hass=h;const sig=this._states().map(s=>s.entity_id+s.last_updated).join('|');if(sig!==this._sig){this._sig=sig;this._render();this._loadTrends();}}
    getCardSize(){return this._config&&this._config.compact?6:10;}
    static getStubConfig(){return{student:'Trent'};}
    _isCourseSensor(s){const a=s.attributes||{};return s.entity_id.startsWith('sensor.')&&('section_id' in a||'assignments' in a||'course' in a)&&('student' in a);}
    _states(){const stu=(this._config.student||'').toLowerCase();const hide=!this._config.show_empty;
      return Object.values(this._hass.states).filter(s=>{
        if(!this._isCourseSensor(s))return false;
        const a=s.attributes||{};const name=String(a.student||'').toLowerCase();const eid=s.entity_id.toLowerCase();
        if(!(name===stu||name.includes(stu)||eid.includes('_'+stu.replace(/\s+/g,'_')+'_')||eid.includes('powerschool_'+stu)))return false;
        if(/_(grade_average|assignment_count|course_count|missing_assignments|late_assignments|ungraded_assignments|graded_assignments)$/.test(eid))return false;
        if(hide&&['unknown','unavailable'].includes(s.state))return false;
        return true;
      });}
    async _refresh(){if(!this._hass||this._refreshing)return;this._refreshing=true;this._sig='';this._render();
      try{await this._hass.callService('powerschool','refresh',{});}catch(e){try{const ids=this._states().map(s=>s.entity_id);if(ids.length)await this._hass.callService('homeassistant','update_entity',{entity_id:ids});}catch(_){}}
      this._refreshing=false;this._sig='';this._trendLoaded=false;this._render();this._loadTrends();}
    async _loadTrends(){const ids=this._states().map(s=>s.entity_id);if(!ids.length)return;
      if(this._trendLoading)return;this._trendLoading=true;
      const DAYS=14;const end=new Date();const start=new Date(end.getTime()-DAYS*24*3600*1000);
      const path=`history/period/${start.toISOString()}?filter_entity_id=${encodeURIComponent(ids.join(','))}&minimal_response`;
      try{const res=await this._hass.callApi('GET',path);
        this._trend=this._trend||{};this._spark=this._spark||{};
        (res||[]).forEach(series=>{if(!series||!series.length)return;
          const id=(series.find(p=>p.entity_id)||series[0]).entity_id;if(!id)return;
          const pts=series.map(p=>({t:new Date(p.last_changed||p.last_updated).getTime(),v:parseFloat(p.state)})).filter(p=>!isNaN(p.v)).sort((a,b)=>a.t-b.t);
          let sample=pts;if(pts.length>12){const step=Math.ceil(pts.length/12);sample=pts.filter((_,i)=>i%step===0||i===pts.length-1);}
          this._spark[id]=sample;
          if(pts.length>=2){const diff=pts[pts.length-1].v-pts[0].v;if(diff>0.25)this._trend[id]='up';else if(diff<-0.25)this._trend[id]='down';else this._trend[id]='flat';}
        });
        this._trendLoaded=true;this._trendLoading=false;this._render();
      }catch(e){this._trendLoaded=true;this._trendLoading=false;}
    }
    _trendMark(t){if(t==='up')return '<ha-icon class="up" icon="mdi:trending-up"></ha-icon>';if(t==='down')return '<ha-icon class="down" icon="mdi:trending-down"></ha-icon>';return '';}
    _sparkSvg(pts,dir){if(!pts||pts.length<2)return '';const W=56,H=18;const vs=pts.map(p=>p.v);let min=Math.min(...vs),max=Math.max(...vs);if(max-min<0.5){min-=1;max+=1;}const step=W/(pts.length-1);const poly=pts.map((p,i)=>{const x=(i*step).toFixed(1);const y=(H-((p.v-min)/(max-min))*H).toFixed(1);return x+','+y;}).join(' ');const stroke=dir==='up'?'#8ef0b0':(dir==='down'?'#ffb3a8':'rgba(255,255,255,.7)');return `<svg class="spark" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" aria-hidden="true"><polyline fill="none" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" points="${poly}"/></svg>`;}
    _data(){const cs=this._states().map(s=>{const a=s.attributes;let nm=String(a.friendly_name||s.entity_id).replace(/^PowerSchool\s+/i,'').replace(new RegExp('^'+String(a.student||'\\S+').replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'\\s+','i'),'');
      const p=parseFloat(s.state);const col=palette(nm);
      return{id:s.entity_id,name:nm,pct:isNaN(p)?null:p,letter:isNaN(p)?'\u2013':letter(p),col,a,trend:this._trend[s.entity_id],assignments:(a.assignments||[]).map(x=>Object.assign({},x,{course:nm,col,cid:s.entity_id}))};});
      if(this._config.sort==='grade')cs.sort((x,y)=>(y.pct??-1)-(x.pct??-1));else cs.sort((x,y)=>x.name.localeCompare(y.name));return cs;}
    _grad(c){return `linear-gradient(160deg,${c[0]},${c[1]})`;}
    _home(){const cs=this._data();const nums=cs.map(c=>c.pct).filter(n=>n!=null);const avg=nums.length?Math.round(nums.reduce((a,b)=>a+b,0)/nums.length*10)/10:null;
      let miss=0,late=0;cs.forEach(c=>{(c.assignments||[]).forEach(a=>{if(a.missing)miss++;else if(a.late&&a.percent==null)late++;});});
      const tiles=cs.map(c=>{const mk=this._sparkSvg(this._spark&&this._spark[c.id],c.trend)+this._trendMark(c.trend);
        return `<div class="tile" data-id="${esc(c.id)}"><div class="art" style="background:${this._grad(c.col)}"><div class="l">${esc(c.letter)}</div><div class="p">${mk}${c.pct!=null?Math.round(c.pct)+'%':''}</div></div><div class="nm">${esc(c.name)}</div></div>`;}).join('');
      return `<div class="top"><h2>${esc(this._config.student||'Student')}</h2><button class="btn" type="button" data-a="refresh" title="Refresh"><ha-icon icon="mdi:refresh"></ha-icon></button></div>
        <div class="stats"><div class="st"><b class="${gcls(avg)}">${avg==null?'\u2013':avg+'%'}</b><span>Average</span></div><div class="st"><b>${cs.length}</b><span>Classes</span></div><div class="st"><b>${miss}</b><span>Missing</span></div><div class="st"><b>${late}</b><span>Late</span></div></div>
        <div class="grid">${tiles||'<div class="empty">No courses</div>'}</div><div class="sub" style="margin-top:8px">Tap a class for assignments</div>`;}
    _course(id){const c=this._data().find(x=>x.id===id);if(!c)return `<div class="back" data-a="back">\u2039 Dashboard</div><div class="empty">Course not found</div>`;
      const a=c.a;const as=(c.assignments||[]).slice().sort((x,y)=>(y.due||'').localeCompare(x.due||''));
      const cat={};as.forEach(x=>{if(x.percent!=null&&x.counted_in_final_grade!==false&&x.possible){const k=x.category||'Other';cat[k]=cat[k]||{e:0,p:0,n:0};cat[k].e+=x.earned||0;cat[k].p+=x.possible;cat[k].n++;}});
      const cats=Object.entries(cat).map(([k,v])=>{const p=v.p?v.e/v.p*100:0;return `<div class="row"><div class="mid"><div class="t1">${esc(k)}</div><div class="t2">${v.n} graded</div></div><div class="sc"><b>${Math.round(p)}%</b></div></div>`;}).join('');
      const mk=this._sparkSvg(this._spark&&this._spark[c.id],c.trend)+this._trendMark(c.trend);
      const rows=as.map(x=>{const miss=!!x.missing;const late=!!x.late&&x.percent==null;let score=miss?'Missing':late?'Late':(x.percent!=null?(Math.round(x.percent*10)/10)+'%':'Ungraded');
        return `<div class="row"><div class="mid"><div class="t1">${esc(x.name||'Assignment')}</div><div class="t2">${x.category?esc(x.category)+' \u00b7 ':''}${x.due?esc(x.due):''}</div></div><div class="sc ${gcls(x.percent)}">${score}</div></div>`;}).join('')||'<div class="row"><div class="mid">No assignments</div></div>';
      return `<div class="back" data-a="back"><ha-icon icon="mdi:chevron-left"></ha-icon> Dashboard</div>
        <div class="hero" style="background:${this._grad(c.col)}"><div class="l">${esc(c.letter)}</div><div><div class="n">${esc(c.name)}</div><div class="p">${mk}${c.pct!=null?Math.round(c.pct)+'%':'No grade yet'}</div></div></div>
        <div class="stats"><div class="st"><b>${a.assignment_count??as.length}</b><span>Total</span></div><div class="st"><b>${a.graded_assignments??'\u2013'}</b><span>Graded</span></div><div class="st"><b>${a.missing??0}</b><span>Missing</span></div><div class="st"><b>${a.late??0}</b><span>Late</span></div></div>
        ${cats?`<div class="sec">Categories</div><div class="card">${cats}</div>`:''}
        <div class="sec">Assignments</div><div class="card">${rows}</div>`;}
    _render(){if(!this._hass||!this._config||!this.shadowRoot)return;const v=this._view;
      const body=v.t==='home'?this._home():this._course(v.id);
      this.shadowRoot.innerHTML=`<style>
:host{display:block}ha-card{overflow:hidden;background:transparent;box-shadow:none;border:none}
.wrap{max-width:900px;margin:0 auto;padding:0 4px 16px}
.top{display:flex;align-items:center;gap:8px;padding:8px 4px 12px}
.top h2{margin:0;font-size:22px;font-weight:600;flex:1;color:var(--primary-text-color)}
.sub{color:var(--secondary-text-color);font-size:14px}
.sec{font-size:17px;color:var(--secondary-text-color);margin:18px 4px 8px;font-weight:500}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
@media(min-width:700px){.grid{grid-template-columns:repeat(3,1fr)}}
.tile{border-radius:16px;overflow:hidden;background:var(--card-background-color);border:1px solid var(--divider-color);cursor:pointer}
.tile:active{transform:scale(.98)}
.art{height:96px;position:relative;display:flex;align-items:center;justify-content:center;color:#fff}
.art .l{font-size:58px;font-weight:600;line-height:1}
.art .p{position:absolute;top:8px;right:12px;font-size:20px;font-weight:600;display:flex;align-items:center;gap:2px}
.art .p ha-icon{--mdc-icon-size:18px}.art .p ha-icon.up{color:#8ef0b0}.art .p ha-icon.down{color:#ffb3a8}
.nm{padding:12px 12px 14px;font-size:16px;color:var(--primary-text-color)}
.btn{width:36px;height:36px;border-radius:50%;border:none;background:var(--secondary-background-color);cursor:pointer;display:inline-flex;align-items:center;justify-content:center}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px}
.st{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:12px;padding:8px;text-align:center}
.st b{display:block;font-size:20px;color:var(--primary-text-color)}.st span{font-size:12px;color:var(--secondary-text-color)}
.ga{color:#2e9e5b}.gb{color:#3a86c8}.gc{color:#d0921f}.gf{color:#c8443a}
.card{background:var(--card-background-color);border-radius:16px;border:1px solid var(--divider-color);overflow:hidden}
.row{display:flex;gap:12px;padding:12px 14px;align-items:center;border-bottom:1px solid var(--divider-color)}.row:last-child{border-bottom:none}
.mid{flex:1;min-width:0}.t1{font-weight:600;font-size:16px}.t2{font-size:14px;color:var(--secondary-text-color)}
.sc{text-align:right;flex:none;font-weight:600}
.back{display:flex;align-items:center;gap:4px;cursor:pointer;color:var(--primary-color);font-size:16px;padding:8px 4px}
.hero{border-radius:16px;color:#fff;padding:18px;display:flex;align-items:center;gap:16px;margin-bottom:12px}
.hero .l{font-size:64px;font-weight:600;line-height:1}.hero .n{font-size:20px;font-weight:600}.hero .p{font-size:16px;opacity:.9;display:flex;align-items:center;gap:4px}
.hero .p ha-icon{--mdc-icon-size:18px}.hero .p ha-icon.up{color:#8ef0b0}.hero .p ha-icon.down{color:#ffb3a8}
.spark{display:inline-block;vertical-align:middle;opacity:.95}
.empty{padding:28px;text-align:center;color:var(--secondary-text-color)}
</style><ha-card><div class="wrap">${body}</div></ha-card>`;
      const btn=this.shadowRoot.querySelector('[data-a="refresh"]');
      if(btn)btn.onclick=e=>{e.stopPropagation();this._refresh();};
      this.shadowRoot.querySelectorAll('.tile[data-id]').forEach(el=>{el.onclick=()=>{this._view={t:'course',id:el.dataset.id};this._render();};});
      const back=this.shadowRoot.querySelector('[data-a="back"]');
      if(back)back.onclick=()=>{this._view={t:'home'};this._render();};
    }
  }
  customElements.define('powerschool-v2-card',PowerSchoolV2Card);
}
window.customCards=window.customCards||[];
if(!window.customCards.find(c=>c.type==='powerschool-v2-card')){
  window.customCards.push({type:'powerschool-v2-card',name:'PowerSchool V2 (App)',description:'App-style PowerSchool card with course drill-down, categories, and 14-day grade sparklines',preview:true});
}
