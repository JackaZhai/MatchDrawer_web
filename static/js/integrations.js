/* ============================================
   Integrations (chat providers + custom API host)
   Kept separate to avoid destabilizing the main app.js.
   ============================================ */

(function () {
  function $(id) {
    return document.getElementById(id);
  }

  function applyChatProviderUI() {
    const sel = $('chatProviderSelect');
    const keyInput = $('chatApiKeyInput');
    if (sel) {
      const provider = localStorage.getItem('chatProvider') || 'grsai';
      sel.value = provider;
      if (window.APIService && window.APIService.setChatProvider) {
        window.APIService.setChatProvider(provider);
      }
    }
    if (keyInput) {
      const key = localStorage.getItem('chatApiKey') || '';
      keyInput.value = key;
      if (window.APIService && window.APIService.setChatApiKey) {
        window.APIService.setChatApiKey(key);
      }
    }
  }

  function bindIntegrationEvents() {
    const chatProviderSelect = $('chatProviderSelect');
    if (chatProviderSelect) chatProviderSelect.addEventListener('change', () => {
      localStorage.setItem('chatProvider', chatProviderSelect.value);
      if (window.APIService && window.APIService.setChatProvider) {
        window.APIService.setChatProvider(chatProviderSelect.value);
      }
    });

    const chatApiKeyInput = $('chatApiKeyInput');
    if (chatApiKeyInput) chatApiKeyInput.addEventListener('blur', () => {
      const v = (chatApiKeyInput.value || '').trim();
      localStorage.setItem('chatApiKey', v);
      if (window.APIService && window.APIService.setChatApiKey) {
        window.APIService.setChatApiKey(v);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    applyChatProviderUI();
    bindIntegrationEvents();
  });
})();
