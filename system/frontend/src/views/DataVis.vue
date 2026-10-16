<template>
  <div class="data-vis-shell">
    <iframe
      :key="visAppUrl"
      :src="visAppUrl"
      class="vis-frame"
      title="OSRI Visualization"
    />
  </div>
</template>

<script setup>
import { computed, inject, ref } from 'vue'

const versionMode = inject('versionMode', ref('global'))
const appBase = (import.meta.env.BASE_URL || '/').replace(/\/$/, '')
const visBasePath = `${appBase}/osri-vis/`
const normalizeDataSource = (mode) => {
  return ['global', 'global_plus', 'aggregation'].includes(mode) ? mode : 'global'
}
const visAppUrl = computed(() => {
  const params = new URLSearchParams({
    data_source: normalizeDataSource(versionMode.value)
  })
  return `${visBasePath}?${params.toString()}`
})
</script>

<style scoped>
.data-vis-shell {
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: white;
}

.vis-frame {
  width: 100%;
  height: 100%;
  min-height: 0;
  border: none;
  display: block;
  background: white;
}
</style>
