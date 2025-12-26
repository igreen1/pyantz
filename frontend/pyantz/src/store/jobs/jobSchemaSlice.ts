/**
 * Store slice for job schemas.
 * @module store/jobs/jobSchemaSlice
 * @author Ian Green
 */
import { createSlice, createAsyncThunk, type PayloadAction } from '@reduxjs/toolkit'
import type { JSONSchema7 } from 'json-schema';
import api from '../../services/api';


interface JobSchemaFetchResponse {
    [job_name: string]: JSONSchema7
}

interface JobSchemasState {
    schemas: JobSchemaFetchResponse
    status: 'idle' | 'loading' | 'succeeded' | 'failed'
    error: string | null
}

const initialState: JobSchemasState = {
    schemas: {},
    status: 'idle',
    error: null,
}


export const availableJobSlice = createSlice({
    name: 'availableJobs',
    initialState,
    reducers: {},
    extraReducers: (builder) => {
    builder
      .addCase(fetchJobSchemas.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchJobSchemas.fulfilled, (state, action: PayloadAction<JobSchemaFetchResponse>) => {
        state.schemas = action.payload
        state.status = 'succeeded'
        state.error = null
      })
      .addCase(fetchJobSchemas.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload as string
      })
  },
})

export const fetchJobSchemas = createAsyncThunk(
  'jobSchemas/fetchAllSchemas',
  async (available_jobs: string[]) => {
    
    const schemas: Promise<JobSchemaFetchResponse>[] = available_jobs.map(
        async (job_name: string) => {
            // Fetch schema for each job
            const response = await api.get("/api/v1.0/jobs/schema/" + job_name)
            return {[job_name]: response.data.json_schema as JSONSchema7}
        }
    )
    const resolvedSchemas = await Promise.all(schemas);
    return resolvedSchemas.reduce((acc, schemaObj) => {
        const [job_name, schema] = Object.entries(schemaObj)[0];
        acc[job_name] = schema;
        return acc;
    }, {} as JobSchemaFetchResponse);

  }
)

export default availableJobSlice.reducer