/**
 * Stores the possible/available jobs
 * by grabbing it from the API.
 */

import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit'
import api from '../../services/api'

interface AvailableJobsState {
  items: string[]
  descriptions: string[]
  status: 'idle' | 'loading' | 'succeeded' | 'failed'
  error: string | null
}

const initialState: AvailableJobsState = {
  items: [],
  descriptions: [],
  status: 'idle',
  error: null,
}


export const availableJobSlice = createSlice({
    name: 'availableJobs',
    initialState,
    reducers: {},
    extraReducers: (builder) => {
    builder
      .addCase(fetchAvailableJobs.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchAvailableJobs.fulfilled, (state, action: PayloadAction<{items: string[], descriptions: string[]}>) => {
        state.items = action.payload.items
        state.descriptions = action.payload.descriptions
        state.status = 'succeeded'
        state.error = null
      })
      .addCase(fetchAvailableJobs.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload as string
      })
  },
})

/**
 * Async thunk to fetch available jobs from the API
 */
export const fetchAvailableJobs = createAsyncThunk(
  'availableJobs/fetchAvailableJobs',
  async () => {
    const response = await api.get('/api/v1.0/jobs/get_all_jobs')
    return {items: response.data.pyantz_jobs as string[], descriptions: response.data.pyantz_job_descriptions as string[]}
  }
)

export default availableJobSlice.reducer
