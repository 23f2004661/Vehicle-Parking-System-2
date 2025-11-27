<script>
import axios from 'axios';
export default{
    name: "Userhistory",
    data(){
        return{
            token: "",
            history: []
        }
    },     
    methods: {
        loadUser(){
            this.token=localStorage.getItem("token")
        },
        async fetchUserHistory(){
            const headers ={
                'Content-Type': "application/json",
                "Authorization": `Bearer ${this.token}`
            }
            const r = await axios.get("http://localhost:5000/user/history",{headers: headers})
            console.log(r.data.history)
            this.history = r.data.history
        },
        async downloadHistory() {
            try {
                const headers = {
                    "Authorization": `Bearer ${this.token}`
                };

                // 1️⃣ Start CSV task
                const start = await axios.get(
                    "http://localhost:5000/export_csv",
                    { headers }
                );

                const task_id = start.data.task_id;

                // 2️⃣ Poll until file is ready
                let fileReady = false;
                let fileBlob = null;

                while (!fileReady) {
                    const poll = await axios.get(
                        `http://localhost:5000/api/csv_result/${task_id}`,
                        { responseType: "blob" }
                    );

                    if (poll.status === 202) {
                        await new Promise(resolve => setTimeout(resolve, 1500));
                    } else {
                        fileReady = true;
                        fileBlob = poll.data;
                    }
                }

                // 3️⃣ Download file
                const url = window.URL.createObjectURL(fileBlob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "report.csv";
                a.click();
                window.URL.revokeObjectURL(url);

            } catch (err) {
                console.error("Error downloading file:", err);
            }
        }

    },
    mounted(){
        this.loadUser()
        this.fetchUserHistory()
    }
}
</script>
<template>
<div v-if="token" id="main" class="container-lg justify-content-center">
    <div class="row">
        <div class="col"><h2 class="bg-primary text-center">User History</h2></div>
        <div class="col-auto text-end">
        <button class="btn btn-success" @click="downloadHistory">
            Download
        </button>
    </div>
    </div>
    <div class="row">
        <div class="col">
            <table class="table table-hover">
                <thead class="table-light">
                    <tr>
                        <th class="col-2">Lot Name</th>
                        <th class="col-2">Spot Number</th>
                        <th class="col-2">Parking Time</th>
                        <th class="col-2">Leaving Time</th>
                        <th class="col-2">Cost</th>
                        <th class="col-2">Action</th>
                    </tr>
                </thead>   
                <tbody>
                    <tr v-for="res in history" :key="res">
                        <td>{{res.lot_name}}</td>
                        <td>{{res.spot_id}}</td>
                        <td>{{res.parking_time_stamp}}</td>
                        <td>{{res.leaving_time_stamp}}</td>
                        <td>{{res.parking_cost}}</td>
                        <td v-if="res.leaving_time_stamp === null">
                            <router-link to="/user/release">Release</router-link>
                        </td>
                        <td v-else class="text-success">Parked Out</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</div>
<div v-else>
    <h1 class="text-danger">Please log in first</h1>
</div>
</template>
<style>

</style>

