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
const visAppUrl = computed(() => `/osri-vis/?data_source=${versionMode.value === 'aggregation' ? 'aggregation' : 'global'}`)
</script>

<style scoped>
.data-vis-shell {
  height: calc(100vh - 80px);
  min-height: calc(100vh - 80px);
  overflow: hidden;
  background: white;
}

.vis-frame {
  width: 100%;
  height: 100%;
  min-height: calc(100vh - 80px);
  border: none;
  display: block;
  background: white;
}

@media (max-width: 900px) {
  .data-vis-shell {
    height: calc(100vh - 148px);
    min-height: calc(100vh - 148px);
  }

  .vis-frame {
    min-height: calc(100vh - 148px);
  }
}
</style>
