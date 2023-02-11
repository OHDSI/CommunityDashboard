import { inject } from "@loopback/core";
import { model, property } from "@loopback/repository";
import { requestBody, RestBindings, Response, oas, param, getJsonSchema, SchemaObject } from "@loopback/rest";
import { GitHubDataSource } from "../datasources";
import { scan } from "../functions/scan";
import { Scan, ScanLog } from "../models";
import { ScanRepository } from "../repositories";
import { GitHub } from "../services";

@model()
export class Pat {
  @property({
    required: true
  })
  user: string
  @property({
    required: true
  })
  token: string
}

@model()
export class ScanParameters {
  @property({
    required: true
  })
  org: string
  // @property({
  // })
  // pat?: Pat
}

export class CommunityDashboardController {
  constructor(
    @inject('services.GitHub')
    protected github: GitHub,
    @inject('datasources.GitHub')
    protected dataSource: GitHubDataSource,
    @inject('repositories.ScanRepository')
    protected scanRepository: ScanRepository,
    @inject(RestBindings.Http.RESPONSE) 
    protected response: Response,
  ) {}

  @oas.post('community-dashboard/scans')
  @oas.response(202, Scan)
  async scanCreate(
    @requestBody({
      required: true,
    }) parameters: ScanParameters
  ) {
    const scanEntity = await this.scanRepository.create(new Scan({...parameters}))
    scan(this.github, this.scanRepository, scanEntity, parameters)
    this.response.status(202)
    return scanEntity
  }


  @oas.get('community-dashboard/scans/{id}/logs')
  @oas.response(200, {
    type: "array",
    items: getJsonSchema(ScanLog) as object
  })
  async scanLogsFind(
    @param.path.number('id') id: number
  ): Promise<ScanLog[]> {
    const scanLogs = await this.scanRepository.scanLogs(id).find()
    return scanLogs
  }
}
