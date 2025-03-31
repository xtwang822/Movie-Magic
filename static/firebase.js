
fetch('/firebase-config')
  .then(response => response.json())
  .then(config => {
      if (!config || config.error) {
          throw new Error("Invalid Firebase configuration received.");
      }

      console.log("✅ Firebase config loaded:", config);

      if (!firebase.apps.length) {
          firebase.initializeApp(config);
      }

      // Now handle authentication state changes
      firebase.auth().onAuthStateChanged((user) => {
          const userInfoDiv = document.getElementById("user-info");
          if (user) {
              userInfoDiv.innerHTML = `
                  Logged in as: ${user.email}
                  <button onclick="logout()">Sign Out</button>
                  <a href="#" onclick="goToProfile()">My Profile</a>
              `;
          } else {
              userInfoDiv.innerHTML = `
                  <button onclick="showLoginPrompt()">Sign In / Register</button>
              `;
          }
      });
  })
  .catch(error => {
      console.error("🔥 Error loading Firebase config:", error);
  });



// ✅ Initialize Firebase (ensure it's only initialized once)
if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}

// ✅ Handle authentication state changes
firebase.auth().onAuthStateChanged((user) => {
    const userInfoDiv = document.getElementById("user-info");

    if (user) {
        // 🔹 If logged in, show email + logout + profile
        userInfoDiv.innerHTML = `
      Logged in as: ${user.email}
      <button onclick="logout()">Sign Out</button>
      <a href="/profile">My Profile</a>
    `;
    } else {
        // 🔹 If NOT logged in, show login button
        userInfoDiv.innerHTML = `
      <button onclick="showLoginPrompt()">Sign In / Register</button>
    `;
    }
});

// ✅ Logout function
function logout() {
    firebase.auth().signOut().then(() => {
        alert("You have been logged out.");
        location.reload();
    });
}

// ✅ Show login/register prompt
function showLoginPrompt() {
    const email = prompt("Enter your email:");
    const password = prompt("Enter your password:");

    if (email && password) {
        firebase.auth().signInWithEmailAndPassword(email, password)
            .then(() => {
                alert("Login successful!");
                location.reload();
            })
            .catch((error) => {
                if (error.code === "auth/user-not-found") {
                    firebase.auth().createUserWithEmailAndPassword(email, password)
                        .then(() => alert("Registration successful."))
                        .catch(err => alert("Registration failed: " + err.message));
                } else {
                    alert("Login failed: " + error.message);
                }
            });
    }
}

function goToProfile() {
    firebase.auth().currentUser.getIdToken(true)
        .then((idToken) => {
            fetch(`/profile`, {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${idToken}`  // ✅ Send token in header
                }
            })
                .then(response => {
                    if (response.status === 401) {
                        alert("You need to be signed in to access your profile.");
                        return;
                    }
                    return response.text();  // ✅ Get response as text (HTML)
                })
                .then(html => {
                    if (html) {
                        document.body.innerHTML = html;  // ✅ Load profile page dynamically
                    }
                })
                .catch(error => {
                    console.error("Error accessing profile:", error);
                    alert("Error accessing profile.");
                });
        })
        .catch((error) => {
            console.error("Failed to get Firebase ID token:", error);
            alert("You need to be signed in.");
        });
}


// ✅ Handle authentication state changes
firebase.auth().onAuthStateChanged((user) => {
    const userInfoDiv = document.getElementById("user-info");

    if (user) {
        // 🔹 Show profile link and logout button
        userInfoDiv.innerHTML = `
      Logged in as: ${user.email}
      <button onclick="logout()">Sign Out</button>
      <a href="#" onclick="goToProfile()">My Profile</a>
    `;
    } else {
        // 🔹 Show login button
        userInfoDiv.innerHTML = `
      <button onclick="showLoginPrompt()">Sign In / Register</button>
    `;
    }
});

function addFavorite(movieId) {
    firebase.auth().currentUser.getIdToken(true)
        .then((idToken) => {
            fetch(`/favorite/${movieId}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${idToken}`  // ✅ Ensure the token is sent
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert("Error: " + data.error);
                    } else {
                        alert("✅ " + data.message);
                    }
                })
                .catch(err => console.error("Request failed:", err));
        })
        .catch((error) => {
            console.error("Failed to get Firebase ID token:", error);
            alert("You need to be signed in to add favorites.");
        });
}

