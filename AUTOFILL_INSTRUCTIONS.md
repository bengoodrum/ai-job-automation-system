# Job Assistant Browser Autofill Helper

## Files added
- `autofill_profile.json` — your profile data for autofill
- `autofill_snippet.js` — the browser autofill helper script

## Setup

1. Open `autofill_profile.json` and replace the placeholder values with your real details.
2. Keep `autofill_snippet.js` available for copy/paste or bookmarklet creation.

## How to use in Safari or Chrome on Mac

### Option 1: Run in browser console
1. Open the job application page in Safari or Chrome.
2. Open the developer console:
   - Safari: `Option+Command+C`
   - Chrome: `Command+Option+J`
3. Copy the entire contents of `autofill_snippet.js` and paste it into the console.
4. Press Enter.
5. Review the checklist printed in the console.
6. Manually submit only after verifying all fields.

### Option 2: Create a bookmarklet in Chrome
1. Open Chrome and go to `Bookmarks > Bookmark manager`.
2. Add a new bookmark.
3. Set the bookmark name to `Job Autofill`.
4. Set the URL to a JavaScript bookmarklet that wraps the script.
5. Use the following bookmarklet template, replacing the placeholder profile values with your actual info:

```javascript
javascript:(function(){
  const profile={name:'Your Name',email:'you@example.com',phone:'555-123-4567',city:'San Francisco',state:'CA',linkedin:'https://www.linkedin.com/in/yourprofile',workAuthorization:'Authorized to work in the U.S.',startAvailability:'Immediately',salaryExpectation:'$100,000'};
  const [firstName,...rest]=profile.name.trim().split(' ');const lastName=rest.join(' ');
  const fieldMappings=[{keys:['email','e-mail'],value:profile.email},{keys:['phone','mobile','telephone','cell'],value:profile.phone},{keys:['first name','firstname','givenname','given name'],value:firstName},{keys:['last name','lastname','surname','familyname','family name'],value:lastName},{keys:['name','full name'],value:profile.name},{keys:['linkedin'],value:profile.linkedin},{keys:['address','street','street address'],value:''},{keys:['city','town'],value:profile.city},{keys:['state','province','region'],value:profile.state},{keys:['zip','postal code','postcode'],value:''},{keys:['start date','start availability','available','availability'],value:profile.startAvailability},{keys:['salary','compensation','pay','desired pay'],value:profile.salaryExpectation},{keys:['work authorization','work auth','authorized to work'],value:profile.workAuthorization}];
  const normalize=t=>(''+(t||'')).trim().toLowerCase();
  const fieldText=e=>{const label=e.id?document.querySelector('label[for="'+e.id+'"]'):null;const labelText=label?label.innerText:'';return[e.name,e.id,e.placeholder,e.type,e.getAttribute('aria-label'),labelText].filter(Boolean).join(' ').toLowerCase();};
  const isVisible=e=>{if(e.offsetParent===null)return false;const s=window.getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&s.opacity!=='0';};
  const setValue=(e,v)=>{if(e.tagName==='SELECT'){const o=Array.from(e.options).find(opt=>normalize(opt.textContent).includes(normalize(v)));if(o)e.value=o.value;}else if(e.tagName==='INPUT'||e.tagName==='TEXTAREA'){e.value=v;}if(typeof e.dispatchEvent==='function'){e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));}};
  let filled=0,skipped=0;document.querySelectorAll('input,textarea,select').forEach(e=>{if(e.disabled||e.readOnly||!isVisible(e)||['submit','button','reset','image','file','password'].includes(e.type))return;const text=fieldText(e);let matched=false;for(const m of fieldMappings){if(!m.value)continue;if(m.keys.some(k=>text.includes(k))){setValue(e,m.value);matched=true;filled++;break;}}if(!matched)skipped++;});console.log('Autofill helper finished.');console.log('Fields filled:',filled);console.log('Fields skipped (left blank):',skipped);console.log('\nReview checklist before submitting:');console.log('1. Verify every filled field is correct and up to date.');console.log('2. Confirm job-specific fields such as title, location, and salary response.');console.log('3. Do not submit until you have checked for CAPTCHAs, login prompts, and hidden required fields.');console.log('4. Leave unknown or unsupported fields blank and fill them manually.');console.log('5. This helper does not submit the form automatically. Submit only after review.');
})();
```

### Option 3: Create a bookmarklet in Safari
1. Open Safari and enable the Bookmarks bar if needed: `View > Show Favorites Bar`.
2. Create a new bookmark in the Favorites bar.
3. Edit the bookmark and replace the URL with the same JavaScript bookmarklet code from above.
4. Save it.
5. Visit the job application page and click the bookmarklet.
6. Review the checklist printed in the console and then submit manually.

## Important safety reminders
- This helper does not submit applications automatically.
- Do not use it to bypass CAPTCHAs, logins, rate limits, or anti-bot systems.
- Always verify the filled fields manually before clicking submit.
- Leave any unknown or unsupported fields blank and fill them yourself.

## Notes
- The helper matches common field names like `email`, `phone`, `first name`, `last name`, `LinkedIn`, `city`, `state`, `zip`, `start date`, and `salary`.
- If a field is not recognized, the script leaves it blank.
