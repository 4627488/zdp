<template>
    <v-app>
        <v-app-bar color="primary" density="compact">
            <v-app-bar-title>Software Reliability Prediction System</v-app-bar-title>
        </v-app-bar>

        <v-main class="bg-grey-lighten-4">
            <v-container>
                <v-row>
                    <!-- Left Panel: Controls -->
                    <v-col cols="12" md="4">
                        <v-card class="mb-4">
                            <v-card-title>Configuration</v-card-title>
                            <v-card-text>
                                <!-- File Upload -->
                                <v-file-input label="Upload Data (CSV)" accept=".csv" prepend-icon="mdi-file-delimited"
                                    variant="outlined" @change="handleFileUpload" :loading="parsing"></v-file-input>
                                <div class="text-caption text-grey mb-4">
                                    * CSV must contain a 'tbf' or 'TBF' column.
                                </div>

                                <!-- Data Preview -->
                                <v-expand-transition>
                                    <div v-if="tbfData.length > 0">
                                        <v-alert type="success" variant="tonal" density="compact" class="mb-4">
                                            Loaded {{ tbfData.length }} data points.
                                        </v-alert>
                                    </div>
                                </v-expand-transition>

                                <!-- Train/Test Split -->
                                <v-slider v-model="trainRatio" label="Training Ratio" min="0.5" max="0.9" step="0.05"
                                    thumb-label color="primary"></v-slider>
                                <div class="text-caption text-right mb-4">
                                    Train: {{ (trainRatio * 100).toFixed(0) }}% / Test: {{ ((1 - trainRatio) *
                                    100).toFixed(0) }}%
                                </div>

                                <!-- Algorithm Selection -->
                                <div class="text-subtitle-1 mb-2">Algorithms</div>
                                <v-checkbox v-for="algo in availableAlgorithms" :key="algo" v-model="selectedAlgorithms"
                                    :label="algo" :value="algo" density="compact" hide-details
                                    color="primary"></v-checkbox>

                                <v-btn block color="primary" size="large" class="mt-6" @click="runPrediction"
                                    :disabled="tbfData.length === 0 || selectedAlgorithms.length === 0"
                                    :loading="loading">
                                    Analyze & Predict
                                </v-btn>
                            </v-card-text>
                        </v-card>

                        <!-- Metrics Table -->
                        <v-card v-if="results">
                            <v-card-title>Evaluation Metrics</v-card-title>
                            <v-table density="compact">
                                <thead>
                                    <tr>
                                        <th>Model</th>
                                        <th>RMSE</th>
                                        <th>MAE</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="res in results.results" :key="res.name">
                                        <td>{{ res.name }}</td>
                                        <td>{{ res.metrics.rmse ? res.metrics.rmse.toFixed(2) : 'N/A' }}</td>
                                        <td>{{ res.metrics.mae ? res.metrics.mae.toFixed(2) : 'N/A' }}</td>
                                    </tr>
                                </tbody>
                            </v-table>
                        </v-card>
                    </v-col>

                    <!-- Right Panel: Visualization -->
                    <v-col cols="12" md="8">
                        <v-card class="fill-height">
                            <v-card-title>Visualization</v-card-title>
                            <v-card-text style="height: 600px;">
                                <div v-if="!results" class="d-flex justify-center align-center fill-height text-grey">
                                    <div class="text-center">
                                        <v-icon icon="mdi-chart-line" size="64" class="mb-2"></v-icon>
                                        <div>Upload data and run prediction to see results</div>
                                    </div>
                                </div>
                                <ResultsChart v-else :train-time="results.train_time"
                                    :test-time-actual="results.test_time_actual" :results="results.results" />
                            </v-card-text>
                        </v-card>
                    </v-col>
                </v-row>
            </v-container>
        </v-main>
    </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Papa from 'papaparse'
import axios from 'axios'
import ResultsChart from './components/ResultsChart.vue'

const tbfData = ref<number[]>([])
const parsing = ref(false)
const loading = ref(false)
const trainRatio = ref(0.75)
const availableAlgorithms = ['GO', 'JM', 'BP']
const selectedAlgorithms = ref(['GO', 'JM', 'BP'])
const results = ref<any>(null)

const handleFileUpload = (event: any) => {
    const file = event.target.files[0]
    if (!file) return

    parsing.value = true
    Papa.parse(file, {
        header: true,
        dynamicTyping: true,
        skipEmptyLines: true,
        complete: (results: any) => {
            // Look for 'tbf' or 'TBF' column
            const data = results.data
            if (data.length > 0) {
                const firstRow = data[0]
                const key = Object.keys(firstRow).find(k => k.toLowerCase() === 'tbf')

                if (key) {
                    tbfData.value = data.map((row: any) => row[key]).filter((v: any) => typeof v === 'number')
                } else {
                    // Fallback: assume first column if no header match
                    tbfData.value = data.map((row: any) => Object.values(row)[0]).filter((v: any) => typeof v === 'number')
                }
            }
            parsing.value = false
        },
        error: (error: any) => {
            console.error(error)
            parsing.value = false
        }
    })
}

const runPrediction = async () => {
    loading.value = true
    try {
        const response = await axios.post('http://localhost:8000/predict', {
            tbf: tbfData.value,
            train_ratio: trainRatio.value,
            algorithms: selectedAlgorithms.value
        })
        results.value = response.data
    } catch (error) {
        console.error(error)
        alert('Prediction failed. Check console for details.')
    } finally {
        loading.value = false
    }
}
</script>

<style>
html {
    overflow-y: auto;
}
</style>
