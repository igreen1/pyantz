# """Completely wipe out ids of a pipeline.

# When a pipeline is submitted as part of a case matrix,
# the job ids of all the subsequent children within that pipeline must be wiped
# so that the multiple pipelines are completely unique. This also must be done
# for the children of those children.
# """

# import uuid
# from collections.abc import Iterable, Mapping
# from typing import TYPE_CHECKING, Any, get_args, get_origin

# from pydantic import BaseModel

# from .abtrast_job import AbstractJobConfig
# from .parameters.decorators import get_parameters

# if TYPE_CHECKING:
#     from .job import JobConfig
#     from .pipeline import JobPipeline


# def clear_ids(jobs: JobPipeline) -> JobPipeline:
#     """Wipe the job ids but maintain the dependency graph."""


# def _update_ids(jobs: JobPipeline) -> tuple[JobPipeline, dict[str, str]]:
#     """Update the ids and provide an old-to-new mapping of the ids."""
#     id_mapping: dict[str, str] = {}

#     def update_job_id[T: (JobConfig, Mapping[str, Any])](
#         job: T,
#     ) -> T:
#         """Clear the id and replace it with a random one."""
#         nonlocal id_mapping
#         job_id: str
#         if isinstance(job, AbstractJobConfig):
#             job_id = job.job_id
#         else:
#             job_id = str(job["job_id"])  # pyright: ignore[reportUnknownArgumentType]
#         if job_id not in id_mapping:
#             id_mapping[job_id] = str(uuid.uuid4())

#         new_job_id = id_mapping[job_id]
#         if isinstance(job, AbstractJobConfig):
#             return job.model_copy(update={"job_id": new_job_id})
#         return {**job, "job_id": new_job_id}  # pyright: ignore[reportReturnType, reportUnknownVariableType]

#     def update_job_params[T: JobConfig | Mapping[str, Any]](
#         job: T, fields: set[str]
#     ) -> T:

#         for field in fields:
#             if isinstance(job.parameters, JobConfig):
#                 job = job.model_copy(update={

#                 })
#             else:
#                 job.parameters


#         return job

#     def recursively_update[T: (JobConfig, Mapping[str, Any])](job: T) -> T:
#         """Check the parameters of a job and update them."""
#         job = update_job_id(job)
#         joblike_parms = _find_joblike_parameters_with_model(job)
#         if joblike_parms is None:
#             return job
#         single_joblike, iterable_joblike = joblike_parms
#         if not single_joblike and not iterable_joblike:
#             return job

#         return None

#     # modify top-level
#     jobs = [job.model_copy(update={"job_id": str(uuid.uuid4())}) for job in jobs]
#     # for each job, modify its parameters

#     return None


# def _find_joblike_parameters_with_model(
#     job: JobConfig,
# ) -> tuple[Iterable[str], Iterable[str]] | None:
#     """Find parameters which appear to be a job.

#     Returns a tuple of single jobs and iterable job parameters.
#     If not registered, none is returned to signal that this job may
#     have job config parameters, but they aren't registered so we can't tell.
#     """
#     single_job_fields: set[str] = set()
#     iterable_job_fields: set[str] = set()
#     if isinstance(job.parameters, BaseModel):
#         # if parameters have been turned into instance, check types directly
#         for field, value in job.parameters.model_dump().items():
#             if isinstance(value, AbstractJobConfig):
#                 single_job_fields.add(field)
#             if isinstance(value, Iterable) and all(
#                 isinstance(subval, AbstractJobConfig)
#                 for subval in value  # pyright: ignore[reportUnknownVariableType]
#             ):
#                 iterable_job_fields.add(field)
#         return single_job_fields, iterable_job_fields

#     # if parameters are still a mapping, must check against their parameter "end state"
#     # ie., check if the job function has a pyantz parameter connected
#     # then check the *class* of the parameter model for the eventual types to be cast
#     param_model = get_parameters(job.function)
#     if param_model is None:
#         return None

#     for field, field_type in param_model.model_fields.items():
#         type_ = field_type.annotation
#         if type_ is None:
#             continue
#         if issubclass(type_, (AbstractJobConfig,)):
#             single_job_fields.add(field)

#         if (
#             get_origin(type_) is not None
#             and isinstance(get_origin(type_), type)
#             and issubclass(get_origin(type_), Iterable)
#             and any(
#                 issubclass(type_arg, AbstractJobConfig) for type_arg in get_args(type_)
#             )
#         ):
#             iterable_job_fields.add(field)

#     return (
#         single_job_fields,
#         iterable_job_fields,
#     )
