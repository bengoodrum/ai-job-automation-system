/*
  Safe Browser Autofill Helper
  --------------------------------
  1) Update autofill_profile.json with your actual info.
  2) Copy this script into the browser console on a job application page,
     or convert it into a bookmarklet using the provided instructions.
  3) Do NOT use this to auto-submit forms. Review all fields before submitting.
*/
(function () {
  const profile = {
    name: 'Your Name',
    email: 'you@example.com',
    phone: '555-123-4567',
    city: 'San Francisco',
    state: 'CA',
    linkedin: 'https://www.linkedin.com/in/yourprofile',
    workAuthorization: 'Authorized to work in the U.S.',
    startAvailability: 'Immediately',
    salaryExpectation: '$100,000'
  };

  const [firstName, ...restName] = profile.name.trim().split(' ');
  const lastName = restName.join(' ');

  const fieldMappings = [
    { keys: ['email', 'e-mail'], value: profile.email },
    { keys: ['phone', 'mobile', 'telephone', 'cell'], value: profile.phone },
    { keys: ['first name', 'firstname', 'givenname', 'given name'], value: firstName },
    { keys: ['last name', 'lastname', 'surname', 'familyname', 'family name'], value: lastName },
    { keys: ['name', 'full name'], value: profile.name },
    { keys: ['linkedin'], value: profile.linkedin },
    { keys: ['address', 'street', 'street address'], value: '' },
    { keys: ['city', 'town'], value: profile.city },
    { keys: ['state', 'province', 'region'], value: profile.state },
    { keys: ['zip', 'postal code', 'postcode'], value: '' },
    { keys: ['start date', 'start availability', 'available', 'availability'], value: profile.startAvailability },
    { keys: ['salary', 'compensation', 'pay', 'desired pay'], value: profile.salaryExpectation },
    { keys: ['work authorization', 'work auth', 'authorized to work'], value: profile.workAuthorization }
  ];

  const normalize = text => (text || '').toString().trim().toLowerCase();
  const fieldText = el => {
    const label = el.id ? document.querySelector(`label[for="${el.id}"]`) : null;
    const labelText = label ? label.innerText : '';
    return [el.name, el.id, el.placeholder, el.type, el.getAttribute('aria-label'), labelText]
      .filter(Boolean)
      .join(' ').toLowerCase();
  };

  const isVisible = el => {
    if (el.offsetParent === null) return false;
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
  };

  const setValue = (el, value) => {
    if (el.tagName === 'SELECT') {
      const option = Array.from(el.options).find(opt => normalize(opt.textContent).includes(normalize(value)));
      if (option) {
        el.value = option.value;
      }
    } else if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
      el.value = value;
    }
    if (typeof el.dispatchEvent === 'function') {
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }
  };

  const fillCount = { filled: 0, skipped: 0 };

  document.querySelectorAll('input, textarea, select').forEach(el => {
    if (el.disabled || el.readOnly || !isVisible(el) || el.type === 'submit' || el.type === 'button' || el.type === 'reset' || el.type === 'image' || el.type === 'file' || el.type === 'password') {
      return;
    }

    const combinedText = fieldText(el);
    let didFill = false;

    for (const mapping of fieldMappings) {
      if (!mapping.value) {
        continue;
      }
      if (mapping.keys.some(key => combinedText.includes(key))) {
        setValue(el, mapping.value);
        didFill = true;
        fillCount.filled += 1;
        break;
      }
    }

    if (!didFill) {
      fillCount.skipped += 1;
    }
  });

  console.log('Autofill helper finished.');
  console.log('Fields filled:', fillCount.filled);
  console.log('Fields skipped (left blank):', fillCount.skipped);
  console.log('\nReview checklist before submitting:');
  console.log('1. Verify every filled field is correct and up to date.');
  console.log('2. Confirm job-specific fields such as title, location, and salary response.');
  console.log('3. Do not submit until you have checked for CAPTCHAs, login prompts, and hidden required fields.');
  console.log('4. Leave unknown or unsupported fields blank and fill them manually.');
  console.log('5. This helper does not submit the form automatically. Submit only after review.');
})();
