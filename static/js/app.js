/* ---------------------------------------------------------
   This file is loaded once (layout.html) and exposes helper
   functions globally so inline-onclick can reach them.
----------------------------------------------------------*/

// 1. ——— Firebase config fetched from Flask endpoint ———
fetch('/firebase-config')
  .then(r => r.json())
  .then(cfg => {
    if (cfg.error) throw new Error(cfg.error);
    if (!firebase.apps.length) firebase.initializeApp(cfg);

    // Handle login state for nav bar
    firebase.auth().onAuthStateChanged(updateNav);
  })
  .catch(err => console.error('Firebase init failed:', err));

// 2. ——— Navbar text helpers ———
function updateNav(user) {
  const ui = document.getElementById('user-info');
  if (!ui) return;

  if (user) {
    ui.innerHTML = `
      Logged in as: ${user.email}
      <button onclick="logout()">Sign Out</button>
      <a href="#" onclick="goToProfile()">Favorites</a>
    `;
  } else {
    ui.innerHTML = `<button onclick="showLoginPrompt()">Sign In / Register</button>`;
  }
}

// 3. ——— Auth utility functions ———
window.logout = function logout() {
  firebase.auth().signOut().then(() => location.reload());
};

window.showLoginPrompt = function showLoginPrompt() {
  const email = prompt('Email:');
  const pwd   = prompt('Password:');
  if (!email || !pwd) return;

  firebase.auth().signInWithEmailAndPassword(email, pwd)
    .catch(err => {
      if (err.code === 'auth/user-not-found') {
        return firebase.auth()
                      .createUserWithEmailAndPassword(email, pwd);
      }
      throw err;
    })
    .then(() => location.reload())
    .catch(err => alert(err.message));
};

window.goToProfile = function goToProfile() {
  const user = firebase.auth().currentUser;

  if (!user) {
    alert("You need to be signed in.");
    return;
  }

  user.getIdToken(true)
    .then(idToken => {
      return fetch('/profile', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${idToken}`
        }
      });
    })
    .then(resp => {
      if (resp.status === 401) {
        alert("You need to be signed in to access your profile.");
        return;
      }
      return resp.text();
    })
    .then(html => {
      if (html) {
        document.body.innerHTML = html;
      }
    })
    .catch(err => {
      console.error("Error loading profile:", err);
      alert("Error accessing profile.");
    });
};


// 4. ——— Favorites helpers ———
window.addFavorite = function addFavorite(movieId) {
  firebase.auth().currentUser?.getIdToken(true)
    .then(token =>
      fetch(`/favorite/${movieId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      })
    )
    .then(r => r.json())
    .then(data => alert(data.message || data.error))
    .catch(err => alert(err.message || 'You must be signed in.'));
};

window.removeFavorite = function removeFavorite(movieId) {
  firebase.auth().currentUser?.getIdToken(true)
    .then(token =>
      fetch(`/favorite/remove/${movieId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      })
    )
    .then(async resp => {
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Failed');

      // Optimistic UI update
      const btn = document.querySelector(
        `button[onclick="removeFavorite(${movieId})"]`
      );
      btn?.closest('li')?.remove();

      if (document.querySelectorAll('ul > li').length === 0) {
        document.querySelector('ul')?.remove();
        const p = document.createElement('p');
        p.style.color = '#999';
        p.textContent = 'You have no favorite movies yet. Go explore!';
        document.querySelector('h2').after(p);
      }

      alert(data.message);
    })
    .catch(err => alert(err.message || 'You must be signed in.'));
};

// --- SEARCH BAR HELPER ---------------------------------
window.doSearch = function doSearch() {
  const q = prompt('Search movies / TV shows:');
  if (q) location.href = `/search?q=${encodeURIComponent(q)}`;
};
