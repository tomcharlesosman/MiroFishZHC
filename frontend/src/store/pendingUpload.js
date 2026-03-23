/**
 * Temporary storage for files and the simulation brief before upload.
 * Used to jump from the homepage to Process, where the API call is made.
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  companyWebsiteUrl: '',
  simulationRequirement: '',
  isPending: false
})

export function setPendingUpload(files, requirement, companyWebsiteUrl = '') {
  state.files = files
  state.simulationRequirement = requirement
  state.companyWebsiteUrl = companyWebsiteUrl
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    companyWebsiteUrl: state.companyWebsiteUrl,
    simulationRequirement: state.simulationRequirement,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.files = []
  state.companyWebsiteUrl = ''
  state.simulationRequirement = ''
  state.isPending = false
}

export default state
