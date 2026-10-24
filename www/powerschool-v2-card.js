/* powerschool-v2-card — full app-style card from v2 */
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&','<':'<','>':'>','"':'"',"'":'&#39;'}[c]));
const LET=[[93,'A'],[90,'A-'],[87,'B+'],[83,'B'],[80,'B-'],[77,'C+'],[73,'C'],[70,'C-'],[67,'D+'],[63,'D'],[60,'D-']];
const letter=p=>{if(p==null||isNaN(p))return '\u2013';const r=Math.round(p);for(const [m,l] of LET)if(r>=m)return l;return 'F';};
const gcls=p=>p==null?'':(p>=90?'ga':p>=80?'gb':p>=70?'gc':'gf');
const fmt=v=>v==null?'\u2013':String(Math.round(v*100)/100);
console.info('powerschool-v2-card: use full file from local artifacts if truncated');
if(!customElements.get('powerschool-v2-card')){
  class PowerSchoolV2Card extends HTMLElement{
    constructor(){super();this.attachShadow({mode:'open'});this._view={t:'home'};}
    setConfig(c){this._config=Object.assign({},c);this._view={t:'home'};this._sig='';}
    set hass(h){this._hass=h;this._render();}
    getCardSize(){return this._config&&this._config.compact?6:10;}
    static getStubConfig(){return{student:'Trent'};}
    _states(){
      if(!this._hass||!this._config)return[];
      const stu=String(this._config.student||'').toLowerCase();
      const out=[];
      for(const s of Object.values(this._hass.states)){
        if(!s.entity_id.startsWith('sensor.'))continue;
        const a=s.attributes||{};
        const name=String(a.student||'').toLowerCase();
        const eid=s.entity_id.toLowerCase();
        const isCourse=a.section_id!=null||a.course||a.assignments;
        if(!isCourse)continue;
        if(name===stu||name.includes(stu)||eid.includes('_'+stu.replace(/\s+/g,'_')+'_')||eid.includes('powerschool_'+stu)){
          if(/_(grade_average|assignment_count|course_count|missing_assignments|late_assignments|ungraded_assignments|graded_assignments)$/.test(eid))continue;
          out.push(s);
        }
      }
      out.sort((a,b)=>String(a.attributes.friendly_name||'').localeCompare(String(b.attributes.friendly_name||'')));
      return out;
    }
    async _refresh(){
      if(!this._hass)return;
      try{await this._hass.callService('powerschool','refresh',{});}catch(e){}
      this._sig='';this._render();
    }
    _render(){
      if(!this._hass||!this._config||!this.shadowRoot)return;
      const states=this._states();
      const nums=states.map(s=>parseFloat(s.state)).filter(n=>!isNaN(n));
      const avg=nums.length?Math.round((nums.reduce((a,b)=>a+b,0)/nums.length)*10)/10:null;
      let miss=0,late=0;
      for(const s of states){for(const a of(s.attributes.assignments||[])){if(a.missing)miss++;else if(a.late&&a.percent==null)late++;}}
      const tiles=states.map(s=>{
        const p=parseFloat(s.state);const grade=isNaN(p)?null:p;
        const nm=(s.attributes.friendly_name||'').replace(/^PowerSchool\s+\w+\s+/i,'');
        const asgs=s.attributes.assignments||[];
        const m=asgs.filter(a=>a.missing).length;
        return `<div class="tile" data-id="${esc(s.entity_id)}"><div class="art" style="background:linear-gradient(135deg,#3f8a78,#2a5f52)"><div class="l">${grade==null?'\u2013':letter(grade)}</div>${grade!=null?`<div class="p">${Math.round(grade)}%</div>`:''}</div><div class="nm">${esc(nm)}${m?` <span class="fl bad">${m} miss</span>`:''}</div></div>`;
      }).join('');
      this.shadowRoot.innerHTML=`<style>
        :host{display:block}ha-card{overflow:hidden;background:transparent;box-shadow:none;border:none}
        .wrap{max-width:900px;margin:0 auto;padding:0 4px 16px}
        .top{display:flex;align-items:center;gap:8px;padding:8px 4px 12px}
        .top h2{margin:0;font-size:22px;font-weight:600;flex:1}
        .btn{width:36px;height:36px;border-radius:50%;border:none;background:var(--secondary-background-color);cursor:pointer}
        .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
        @media(min-width:700px){.grid{grid-template-columns:repeat(3,1fr)}}
        .tile{border-radius:16px;overflow:hidden;background:var(--card-background-color);border:1px solid var(--divider-color);cursor:pointer}
        .art{height:96px;position:relative;display:flex;align-items:center;justify-content:center;color:#fff}
        .art .l{font-size:58px;font-weight:600}
        .art .p{position:absolute;top:8px;right:12px;font-size:20px;font-weight:600}
        .nm{padding:12px;font-size:16px}
        .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px}
        .st{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:12px;padding:8px;text-align:center}
        .st b{display:block;font-size:20px}.st span{font-size:12px;color:var(--secondary-text-color)}
        .fl.bad{background:#c8443a22;color:#c8443a;font-size:12px;padding:1px 7px;border-radius:8px}
        .detail{margin-top:12px}.row{display:flex;gap:12px;padding:10px 12px;border-bottom:1px solid var(--divider-color);align-items:center}
        .mid{flex:1}.t1{font-weight:600}.t2{font-size:13px;color:var(--secondary-text-color)}.sc{text-align:right;font-weight:600}
        .back{color:var(--primary-color);cursor:pointer;padding:8px 4px}
        .ga{color:#2e9e5b}.gb{color:#3a86c8}.gc{color:#d0921f}.gf{color:#c8443a}
      </style><ha-card><div class="wrap">
        <div class="top"><h2>${esc(this._config.student||'Student')}</h2>
        <button class="btn" type="button" data-a="refresh" title="Refresh"><ha-icon icon="mdi:refresh"></ha-icon></button></div>
        <div class="stats"><div class="st"><b class="${gcls(avg)}">${avg==null?'\u2013':avg+'%'}</b><span>Average</span></div>
        <div class="st"><b>${states.length}</b><span>Classes</span></div>
        <div class="st"><b>${miss}</b><span>Missing</span></div>
        <div class="st"><b>${late}</b><span>Late</span></div></div>
        ${this._view.t==='course'?this._courseDetail():`<div class="grid">${tiles}</div><div style="margin-top:8px;color:var(--secondary-text-color);font-size:13px">Tap a class for assignments</div>`}
      </div></ha-card>`;
      const btn=this.shadowRoot.querySelector('[data-a="refresh"]');
      if(btn)btn.onclick=e=>{e.stopPropagation();this._refresh();};
      this.shadowRoot.querySelectorAll('.tile[data-id]').forEach(el=>{
        el.onclick=()=>{this._view={t:'course',id:el.dataset.id};this._render();};
      });
      const back=this.shadowRoot.querySelector('[data-a="back"]');
      if(back)back.onclick=()=>{this._view={t:'home'};this._render();};
    }
    _courseDetail(){
      const s=this._hass.states[this._view.id];
      if(!s)return'<div class="back" data-a="back">\u2039 Dashboard</div><div>Not found</div>';
      const p=parseFloat(s.state);const grade=isNaN(p)?null:p;
      const nm=(s.attributes.friendly_name||'').replace(/^PowerSchool\s+\w+\s+/i,'');
      const asgs=(s.attributes.assignments||[]).slice().sort((a,b)=>String(b.due||'').localeCompare(String(a.due||'')));
      const rows=asgs.map(a=>{
        const miss=!!a.missing;const late=!!a.late&&a.percent==null;
        let score=miss?'Missing':late?'Late':(a.percent!=null?(Math.round(a.percent*10)/10)+'%':'Ungraded');
        return `<div class="row"><div class="mid"><div class="t1">${esc(a.name||'Assignment')}</div><div class="t2">${a.category?esc(a.category)+' \u00b7 ':''}${a.due?esc(a.due):''}</div></div><div class="sc ${gcls(a.percent)}">${score}</div></div>`;
      }).join('')||'<div class="row"><div class="mid">No assignments</div></div>';
      return `<div class="back" data-a="back">\u2039 Dashboard</div>
        <div class="art" style="background:linear-gradient(135deg,#3f8a78,#2a5f52);border-radius:16px;margin-bottom:12px"><div class="l">${grade==null?'\u2013':letter(grade)}</div><div class="p">${nm} ${grade!=null?Math.round(grade)+'%':''}</div></div>
        <div class="detail" style="background:var(--card-background-color);border-radius:16px;border:1px solid var(--divider-color)">${rows}</div>`;
    }
  }
  customElements.define('powerschool-v2-card',PowerSchoolV2Card);
}
window.customCards=window.customCards||[];
if(!window.customCards.find(c=>c.type==='powerschool-v2-card')){
  window.customCards.push({type:'powerschool-v2-card',name:'PowerSchool V2 (App)',description:'App-style PowerSchool card with course drill-down',preview:true});
}
