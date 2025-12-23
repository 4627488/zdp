<template>
    <v-app>
        <v-app-bar color="primary" density="compact">
            <v-app-bar-title>Software Reliability Prediction System</v-app-bar-title>
            <template v-slot:extension>
                <v-tabs v-model="activeTab" align-tabs="title">
                    <v-tab value="preprocess">Data Preprocessing</v-tab>
                    <v-tab value="predict">Model Prediction</v-tab>
                </v-tabs>
            </template>
        </v-app-bar>

        <v-main class="bg-grey-lighten-4">
            <v-container fluid>
                <v-window v-model="activeTab">
                    <!-- Preprocessing Tab -->
                    <v-window-item value="preprocess">
                        <v-row>
                            <v-col cols="12" md="4">
                                <v-card class="mb-4">
                                    <v-card-title>Data & Configuration</v-card-title>
                                    <v-card-text>
                                        <v-file-input label="Upload Data (CSV)" accept=".csv"
                                            prepend-icon="mdi-file-delimited" variant="outlined"
                                            @change="handleFileUpload" :loading="parsing"
                                            hint="Required column: 'tbf' or 'TBF'" persistent-hint></v-file-input>

                                        <v-expand-transition>
                                            <div v-if="tbfData.length > 0">
                                                <v-alert type="success" variant="tonal" density="compact" class="mb-4">
                                                    Loaded {{ tbfData.length }} records.
                                                </v-alert>
                                            </div>
                                        </v-expand-transition>

                                        <v-divider class="my-4"></v-divider>
                                        <div class="text-subtitle-1 mb-2">Preprocessing Options</div>

                                        <v-switch v-model="preprocessConfig.handle_missing"
                                            label="Handle Missing Values" color="primary" density="compact"
                                            hide-details></v-switch>
                                        <v-select v-if="preprocessConfig.handle_missing"
                                            v-model="preprocessConfig.missing_strategy"
                                            :items="['mean', 'median', 'drop']" label="Strategy" density="compact"
                                            variant="outlined" class="ml-4 mt-2"></v-select>

                                        <v-switch v-model="preprocessConfig.detect_outliers" label="Detect Outliers"
                                            color="primary" density="compact" hide-details></v-switch>
                                        <v-select v-if="preprocessConfig.detect_outliers"
                                            v-model="preprocessConfig.outlier_method" :items="['zscore', 'iqr']"
                                            label="Method" density="compact" variant="outlined"
                                            class="ml-4 mt-2"></v-select>

                                        <v-switch v-model="preprocessConfig.normalize" label="Normalization"
                                            color="primary" density="compact" hide-details></v-switch>
                                        <v-select v-if="preprocessConfig.normalize"
                                            v-model="preprocessConfig.normalization_method"
                                            :items="['minmax', 'zscore']" label="Method" density="compact"
                                            variant="outlined" class="ml-4 mt-2"></v-select>

                                        <v-btn block color="secondary" class="mt-6" @click="runPreprocessing"
                                            :disabled="tbfData.length === 0" :loading="processing">
                                            Run Preprocessing
                                        </v-btn>
                                    </v-card-text>
                                </v-card>

                                <v-card v-if="preprocessResults">
                                    <v-card-title>Statistics</v-card-title>
                                    <v-table density="compact">
                                        <tbody>
                                            <tr>
                                                <td>Original Count</td>
                                                <td>{{ preprocessResults.stats.original_count }}</td>
                                            </tr>
                                            <tr>
                                                <td>Processed Count</td>
                                                <td>{{ preprocessResults.stats.processed_count }}</td>
                                            </tr>
                                            <tr>
                                                <td>Mean</td>
                                                <td>{{ preprocessResults.stats.mean.toFixed(2) }}</td>
                                            </tr>
                                            <tr>
                                                <td>Std Dev</td>
                                                <td>{{ preprocessResults.stats.std.toFixed(2) }}</td>
                                            </tr>
                                        </tbody>
                                    </v-table>
                                </v-card>
                            </v-col>

                            <v-col cols="12" md="8">
                                <v-card class="fill-height">
                                    <v-card-title>Distribution Analysis</v-card-title>
                                    <v-card-text style="height: 600px;">
                                        <div v-if="!preprocessResults"
                                            class="d-flex justify-center align-center fill-height text-grey">
                                            <div class="text-center">
                                                <v-icon icon="mdi-chart-bar" size="64" class="mb-2"></v-icon>
                                                <div>Run preprocessing to view distribution changes</div>
                                            </div>
                                        </div>
                                        <DistributionChart v-else
                                            :original-distribution="preprocessResults.original_distribution"
                                            :processed-distribution="preprocessResults.processed_distribution" />
                                    </v-card-text>
                                </v-card>
                            </v-col>
                        </v-row>
                    </v-window-item>

                    <!-- Prediction Tab -->
                    <v-window-item value="predict">
                        <v-row>
                            <v-col cols="12" md="4">
                                <v-card class="mb-4">
                                    <v-card-title>Model Configuration</v-card-title>
                                    <v-card-text>
                                        <v-alert v-if="processedData.length > 0" type="info" variant="tonal"
                                            density="compact" class="mb-4">
                                            Using processed data ({{ processedData.length }} samples)
                                        </v-alert>
                                        <v-alert v-else type="warning" variant="tonal" density="compact" class="mb-4">
                                            Using raw data ({{ tbfData.length }} samples). Recommend preprocessing
                                            first.
                                        </v-alert>

                                        <v-slider v-model="trainRatio" label="Training Ratio" min="0.5" max="0.9"
                                            step="0.05" thumb-label color="primary"></v-slider>

                                        <div class="text-subtitle-1 mb-2">Select Algorithms</div>
                                        <v-row dense>
                                            <v-col cols="6" v-for="algo in availableAlgorithms" :key="algo">
                                                <v-checkbox v-model="selectedAlgorithms" :label="algo" :value="algo"
                                                    density="compact" hide-details color="primary"></v-checkbox>
                                            </v-col>
                                        </v-row>

                                        <v-btn block color="primary" size="large" class="mt-6" @click="runPrediction"
                                            :disabled="(processedData.length === 0 && tbfData.length === 0) || selectedAlgorithms.length === 0"
                                            :loading="loading">
                                            Train & Predict
                                        </v-btn>
                                    </v-card-text>
                                </v-card>

                                <v-card v-if="results">
                                    <v-card-title class="d-flex justify-space-between align-center">
                                        Metrics
                                        <v-btn icon="mdi-download" size="small" variant="text" @click="exportResults"
                                            title="Export Results (CSV)"></v-btn>
                                    </v-card-title>
                                    <v-table density="compact">
                                        <thead>
                                            <tr>
                                                <th>Model</th>
                                                <th>RMSE
                                                    <v-tooltip activator="parent" location="top">Root Mean Square
                                                        Error</v-tooltip>
                                                </th>
                                                <th>MAE
                                                    <v-tooltip activator="parent" location="top">Mean Absolute
                                                        Error</v-tooltip>
                                                </th>
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

                            <v-col cols="12" md="8">
                                <v-card class="fill-height">
                                    <v-card-title>Prediction Results</v-card-title>
                                    <v-card-text style="height: 600px;">
                                        <div v-if="!results"
                                            class="d-flex justify-center align-center fill-height text-grey">
                                            <div class="text-center">
                                                <v-icon icon="mdi-chart-line" size="64" class="mb-2"></v-icon>
                                                <div>Run prediction to see results</div>
                                            </div>
                                        </div>
                                        <ResultsChart v-else :train-time="results.train_time"
                                            :test-time-actual="results.test_time_actual" :results="results.results" />
                                    </v-card-text>
                                </v-card>
                            </v-col>
                        </v-row>
                    </v-window-item>
                </v-window>
            </v-container>
        </v-main>
    </v-app>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import Papa from 'papaparse'
import axios from 'axios'
import ResultsChart from './components/ResultsChart.vue'
import DistributionChart from './components/DistributionChart.vue'

const activeTab = ref('preprocess')
const tbfData = ref<number[]>([])
const processedData = ref<number[]>([])
const parsing = ref(false)
const loading = ref(false)
const processing = ref(false)

// Preprocessing Config
const preprocessConfig = reactive({
    handle_missing: true,
    missing_strategy: 'mean',
    detect_outliers: true,
    outlier_method: 'zscore',
    outlier_threshold: 3.0,
    normalize: false,
    normalization_method: 'minmax'
})
const preprocessResults = ref<any>(null)

// Prediction Config
const trainRatio = ref(0.75)
const availableAlgorithms = ['GO', 'JM', 'BP', 'Statistical', 'Bayesian', 'LLM']
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
            const data = results.data
            if (data.length > 0) {
                const firstRow = data[0]
                const key = Object.keys(firstRow).find(k => k.toLowerCase() === 'tbf')

                if (key) {
                    tbfData.value = data.map((row: any) => row[key]).filter((v: any) => typeof v === 'number')
                } else {
                    tbfData.value = data.map((row: any) => Object.values(row)[0]).filter((v: any) => typeof v === 'number')
                }
                // Reset processed data when new file loaded
                processedData.value = []
                preprocessResults.value = null
            }
            parsing.value = false
        },
        error: (error: any) => {
            console.error(error)
            parsing.value = false
        }
    })
}

const runPreprocessing = async () => {
    processing.value = true
    try {
        const response = await axios.post('http://localhost:8000/preprocess', {
            data: tbfData.value,
            config: preprocessConfig
        })
        preprocessResults.value = response.data
        processedData.value = response.data.processed_data
    } catch (error) {
        console.error(error)
        alert('Preprocessing failed.')
    } finally {
        processing.value = false
    }
}

const runPrediction = async () => {
    loading.value = true
    // Use processed data if available, otherwise raw
    const dataToUse = processedData.value.length > 0 ? processedData.value : tbfData.value

    try {
        const response = await axios.post('http://localhost:8000/predict', {
            tbf: dataToUse,
            train_ratio: trainRatio.value,
            algorithms: selectedAlgorithms.value
        })
        results.value = response.data
    } catch (error) {
        console.error(error)
        alert('Prediction failed.')
    } finally {
        loading.value = false
    }
}

const exportResults = () => {
    if (!results.value) return

    const rows = []
    // Header
    const header = ['Index', 'Train/Test', 'Actual Cumulative Time']
    results.value.results.forEach((r: any) => {
        header.push(`${r.name} Prediction`)
    })
    rows.push(header)

    // Data
    const trainLen = results.value.train_time.length
    const testLen = results.value.test_time_actual.length

    // Train rows
    for (let i = 0; i < trainLen; i++) {
        const row = [i + 1, 'Train', results.value.train_time[i]]
        results.value.results.forEach(() => row.push('')) // No predictions for train usually in this format
        rows.push(row)
    }

    // Test rows
    for (let i = 0; i < testLen; i++) {
        const row = [trainLen + i + 1, 'Test', results.value.test_time_actual[i]]
        results.value.results.forEach((r: any) => {
            row.push(r.predicted_cumulative_time[i] || '')
        })
        rows.push(row)
    }

    const csvContent = "data:text/csv;charset=utf-8,"
        + rows.map(e => e.join(",")).join("\n")

    const encodedUri = encodeURI(csvContent)
    const link = document.createElement("a")
    link.setAttribute("href", encodedUri)
    link.setAttribute("download", "reliability_prediction_results.csv")
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
}
</script>

<style>
html {
    overflow-y: auto;
}
</style>
