// Register Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/static/js/service-worker.js')
      .then((registration) => {
        console.log('✅ Service Worker registered successfully:', registration.scope);
      })
      .catch((error) => {
        console.error('❌ Service Worker registration failed:', error);
      });
  });
}

// Install prompt for PWA
let deferredPrompt;
const installButton = document.getElementById('install-pwa-btn');

window.addEventListener('beforeinstallprompt', (e) => {
  console.log('💾 PWA install prompt available');
  e.preventDefault();
  deferredPrompt = e;
  
  // Show install button if it exists
  if (installButton) {
    installButton.style.display = 'block';
  }
});

// Install button click handler
if (installButton) {
  installButton.addEventListener('click', async () => {
    if (!deferredPrompt) {
      return;
    }
    
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    console.log(`User response to install prompt: ${outcome}`);
    deferredPrompt = null;
    installButton.style.display = 'none';
  });
}

// Detect if app is installed
window.addEventListener('appinstalled', () => {
  console.log('✅ FirstAid PWA was installed');
  if (installButton) {
    installButton.style.display = 'none';
  }
});

// Check if running as PWA
if (window.matchMedia('(display-mode: standalone)').matches) {
  console.log('🚀 Running as PWA');
}
