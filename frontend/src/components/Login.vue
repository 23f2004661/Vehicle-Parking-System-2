<script>
import axios from 'axios'
 export default{
    name: "Login",
    data() {
      return {
          username: '',
          password: '',
          error: ''
      };
    },
    methods: {
      loginUser(){
        const headers = {
          "Content-Type": "application/json"
        };
        const body = {
          username: this.username,
          password: this.password
        };
        axios.post("http://localhost:5000/login", body, { headers })
          .then(response => {
            console.log(response.data);
            localStorage.setItem("token",response.data.access_token)
            localStorage.setItem("role",response.data.role)
            if (response.data.role === "user"){
              this.$router.push("/user")
            }
            else{
              this.$router.push("/admin")
            }
          })
          .catch(error => {
            console.log(error.response.data);
            this.error = error.response.data.msg
          });
       }
    }
 }
</script>


<template>
  <div class="container vh-100 d-flex justify-content-center align-items-center">
    <div class="card p-4 shadow-sm" style="width: 100%; max-width: 400px;">
      <h3 class="text-center mb-4">Login</h3>
      <p style="color: red;">{{ this.error }}</p>
      <form @submit.prevent="loginUser">
        <div class="mb-3">
          <label for="username" class="form-label">Username</label>
          <input type="text" v-model="username" class="form-control" id="username" placeholder="Enter username">
        </div>
        <div class="mb-3">
          <label for="password" class="form-label">Password</label>
          <input type="password" v-model="password" class="form-control" id="password" placeholder="Enter password">
        </div>
        <button type="submit" class="btn btn-primary w-100">Login</button>
        <router-link to="/register">Sign up?</router-link>
      </form>
    </div>
  </div>
</template>


<style></style>