/* powerschool-v3-card — alias of v2 with Class Overview registration */
(function(){
  function register(){
    const V2 = customElements.get('powerschool-v2-card');
    if(!V2){
      setTimeout(register, 100);
      return;
    }
    if(customElements.get('powerschool-v3-card')) return;
    class PowerSchoolV3Card extends V2 {}
    customElements.define('powerschool-v3-card', PowerSchoolV3Card);
    window.customCards = window.customCards || [];
    if(!window.customCards.find(c => c.type === 'powerschool-v3-card')){
      window.customCards.push({
        type: 'powerschool-v3-card',
        name: 'PowerSchool V3 (Class Overview)',
        description: 'Class Overview grade tiles (same engine as V2)',
        preview: true
      });
    }
    console.info('powerschool-v3-card registered (alias of v2)');
  }
  if(customElements.get('powerschool-v2-card')) register();
  else customElements.whenDefined('powerschool-v2-card').then(register);
  setTimeout(register, 500);
  setTimeout(register, 2000);
})();
