<template>
    <v-app>
        <v-app-bar color="primary" density="compact">
            <v-app-bar-title>{{ $t('app.title') }}</v-app-bar-title>
            <v-spacer></v-spacer>
            <v-btn-toggle v-model="locale" mandatory density="compact" class="mr-4" color="white" variant="text">
                <v-btn value="zh">中文</v-btn>
                <v-btn value="en">EN</v-btn>
            </v-btn-toggle>
            <template v-slot:extension>
                <v-tabs v-model="activeTab" align-tabs="title">
                    <v-tab value="preprocess">{{ $t('app.tabs.preprocess') }}</v-tab>
                    <v-tab value="predict">{{ $t('app.tabs.predict') }}</v-tab>
                    <v-tab value="analysis" :disabled="!results">{{ $t('app.tabs.analysis') }}</v-tab>
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
                                    <v-card-title>{{ $t('preprocess.title') }}</v-card-title>
                                    <v-card-text>
                                        <v-file-input :label="$t('preprocess.uploadLabel')" accept=".csv"
                                            prepend-icon="mdi-file-delimited" variant="outlined"
                                            @change="handleFileUpload" :loading="parsing"
                                            :hint="$t('preprocess.uploadHint')" persistent-hint></v-file-input>

                                        <v-expand-transition>
                                            <div v-if="tbfData.length > 0">
                                                <v-alert type="success" variant="tonal" density="compact" class="mb-4">
                                                    {{ $t('preprocess.loadedRecords', { n: tbfData.length }) }}
                                                </v-alert>
                                            </div>
                                        </v-expand-transition>

                                        <v-divider class="my-4"></v-divider>
                                        <div class="text-subtitle-1 mb-2">{{ $t('preprocess.optionsTitle') }}</div>

                                        <v-switch v-model="preprocessConfig.handle_missing"
                                            :label="$t('preprocess.handleMissing')" color="primary" density="compact"
                                            hide-details></v-switch>
                                        <v-select v-if="preprocessConfig.handle_missing"
                                            v-model="preprocessConfig.missing_strategy"
                                            :items="['mean', 'median', 'drop']" :label="$t('preprocess.strategy')"
                                            density="compact" variant="outlined" class="ml-4 mt-2"></v-select>

                                        <v-switch v-model="preprocessConfig.detect_outliers"
                                            :label="$t('preprocess.detectOutliers')" color="primary" density="compact"
                                            hide-details></v-switch>
                                        <v-select v-if="preprocessConfig.detect_outliers"
                                            v-model="preprocessConfig.outlier_method" :items="['zscore', 'iqr']"
                                            :label="$t('preprocess.method')" density="compact" variant="outlined"
                                            class="ml-4 mt-2"></v-select>

                                        <v-switch v-model="preprocessConfig.normalize"
                                            :label="$t('preprocess.normalization')" color="primary" density="compact"
                                            hide-details></v-switch>
                                        <v-select v-if="preprocessConfig.normalize"
                                            v-model="preprocessConfig.normalization_method"
                                            :items="['minmax', 'zscore']" :label="$t('preprocess.method')"
                                            density="compact" variant="outlined" class="ml-4 mt-2"></v-select>

                                        <v-btn block color="secondary" class="mt-6" @click="runPreprocessing"
                                            :disabled="tbfData.length === 0" :loading="processing">
                                            {{ $t('preprocess.runBtn') }}
                                        </v-btn>
                                    </v-card-text>
                                </v-card>

                                <v-card v-if="preprocessResults">
                                    <v-card-title>{{ $t('preprocess.statsTitle') }}</v-card-title>
                                    <v-table density="compact">
                                        <tbody>
                                            <tr>
                                                <td>{{ $t('preprocess.stats.originalCount') }}</td>
                                                <td>{{ preprocessResults.stats.original_count }}</td>
                                            </tr>
                                            <tr>
                                                <td>{{ $t('preprocess.stats.processedCount') }}</td>
                                                <td>{{ preprocessResults.stats.processed_count }}</td>
                                            </tr>
                                            <tr>
                                                <td>{{ $t('preprocess.stats.mean') }}</td>
                                                <td>{{ preprocessResults.stats.mean.toFixed(2) }}</td>
                                            </tr>
                                            <tr>
                                                <td>{{ $t('preprocess.stats.stdDev') }}</td>
                                                <td>{{ preprocessResults.stats.std.toFixed(2) }}</td>
                                            </tr>
                                        </tbody>
                                    </v-table>
                                </v-card>
                            </v-col>

                            <v-col cols="12" md="8">
                                <v-card class="fill-height">
                                    <v-card-title>{{ $t('preprocess.distTitle') }}</v-card-title>
                                    <v-card-text style="height: 600px;">
                                        <div v-if="!preprocessResults"
                                            class="d-flex justify-center align-center fill-height text-grey">
                                            <div class="text-center">
                                                <v-icon icon="mdi-chart-bar" size="64" class="mb-2"></v-icon>
                                                <div>{{ $t('preprocess.distPlaceholder') }}</div>
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
                                    <v-card-title>{{ $t('predict.configTitle') }}</v-card-title>
                                    <v-card-text>
                                        <v-alert v-if="processedData.length > 0" type="info" variant="tonal"
                                            density="compact" class="mb-4">
                                            {{ $t('predict.usingProcessed', { n: processedData.length }) }}
                                        </v-alert>
                                        <v-alert v-else type="warning" variant="tonal" density="compact" class="mb-4">
                                            {{ $t('predict.usingRaw', { n: tbfData.length }) }}
                                        </v-alert>

                                        <v-slider v-model="trainRatio" :label="$t('predict.trainRatio')" min="0.5"
                                            max="0.9" step="0.05" thumb-label color="primary"></v-slider>

                                        <div class="text-subtitle-1 mb-2">{{ $t('predict.selectAlgo') }}</div>
                                        <v-row dense>
                                            <v-col cols="6" v-for="algo in availableAlgorithms" :key="algo">
                                                <v-checkbox v-model="selectedAlgorithms" :label="algo" :value="algo"
                                                    density="compact" hide-details color="primary"></v-checkbox>
                                            </v-col>
                                        </v-row>

                                        <v-btn block color="primary" size="large" class="mt-6" @click="runPrediction"
                                            :disabled="(processedData.length === 0 && tbfData.length === 0) || selectedAlgorithms.length === 0"
                                            :loading="loading">
                                            {{ $t('predict.trainBtn') }}
                                        </v-btn>
                                    </v-card-text>
                                </v-card>

                                <v-card v-if="results">
                                    <v-card-title class="d-flex justify-space-between align-center">
                                        {{ $t('predict.metricsTitle') }}
                                        <v-btn icon="mdi-download" size="small" variant="text" @click="exportResults"
                                            :title="$t('predict.exportBtn')"></v-btn>
                                    </v-card-title>
                                    <v-table density="compact">
                                        <thead>
                                            <tr>
                                                <th>{{ $t('predict.columns.model') }}</th>
                                                <th>{{ $t('predict.columns.rmse') }}
                                                    <v-tooltip activator="parent" location="top">{{
                                                        $t('predict.tooltips.rmse')
                                                    }}</v-tooltip>
                                                </th>
                                                <th>{{ $t('predict.columns.mae') }}
                                                    <v-tooltip activator="parent" location="top">{{
                                                        $t('predict.tooltips.mae')
                                                    }}</v-tooltip>
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="res in results.results" :key="res.name">
                                                <td>{{ res.name }}</td>
                                                <td>{{ res.metrics.rmse ? res.metrics.rmse.toFixed(2) : $t('common.na')
                                                }}</td>
                                                <td>{{ res.metrics.mae ? res.metrics.mae.toFixed(2) : $t('common.na') }}
                                                </td>
                                            </tr>
                                        </tbody>
                                    </v-table>
                                </v-card>
                            </v-col>

                            <v-col cols="12" md="8">
                                <v-card class="fill-height">
                                    <v-card-title>{{ $t('predict.resultsTitle') }}</v-card-title>
                                    <v-card-text style="height: 600px;">
                                        <div v-if="!results"
                                            class="d-flex justify-center align-center fill-height text-grey">
                                            <div class="text-center">
                                                <v-icon icon="mdi-chart-line" size="64" class="mb-2"></v-icon>
                                                <div>{{ $t('predict.placeholder') }}</div>
                                            </div>
                                        </div>
                                        <ResultsChart v-else :train-time="results.train_time"
                                            :test-time-actual="results.test_time_actual" :results="results.results" />
                                    </v-card-text>
                                </v-card>
                            </v-col>
                        </v-row>
                    </v-window-item>

                    <!-- Analysis Tab -->
                    <v-window-item value="analysis">
                        <div v-if="!results" class="d-flex justify-center align-center" style="height: 400px;">
                            <div class="text-center text-grey">
                                <v-icon icon="mdi-chart-box-outline" size="64" class="mb-2"></v-icon>
                                <div class="text-h6">{{ $t('analysis.noDataTitle') }}</div>
                                <div>{{ $t('analysis.noDataDesc') }}</div>
                            </div>
                        </div>
                        <AnalysisDashboard v-else :analysis="results.analysis" />
                    </v-window-item>
                </v-window>
            </v-container>
        </v-main>
    </v-app>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import Papa from 'papaparse'
import axios from 'axios'
import ResultsChart from './components/ResultsChart.vue'
import DistributionChart from './components/DistributionChart.vue'
import AnalysisDashboard from './components/AnalysisDashboard.vue'

const { locale, t } = useI18n()
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
        alert(t('common.error'))
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
        alert(t('common.error'))
    } finally {
        loading.value = false
    }
}

const exportResults = () => {
    if (!results.value) return

    const rows = []
    // Header
    const header = [t('export.index'), t('export.trainTest'), t('export.actualTime')]
    results.value.results.forEach((r: any) => {
        header.push(t('export.prediction', { model: r.name }))
    })
    rows.push(header)

    // Data
    const trainLen = results.value.train_time.length
    const testLen = results.value.test_time_actual.length

    // Train rows
    for (let i = 0; i < trainLen; i++) {
        const row = [i + 1, t('export.train'), results.value.train_time[i]]
        results.value.results.forEach(() => row.push('')) // No predictions for train usually in this format
        rows.push(row)
    }

    // Test rows
    for (let i = 0; i < testLen; i++) {
        const row = [trainLen + i + 1, t('export.test'), results.value.test_time_actual[i]]
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
