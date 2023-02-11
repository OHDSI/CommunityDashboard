import {Entity, model, property, belongsTo} from '@loopback/repository';
import {Scan} from './scan.model';

export enum Status {
  COMPLETE = 'complete',
  IN_PROGRESS = 'in progress',
  ERROR = 'error'
}

@model()
export class ScanLog extends Entity {
  @property({
    type: 'number',
    id: true,
    generated: true,
  })
  id?: number;

  @property({
    type: 'string',
    required: true,
    jsonSchema: {
      enum: Object.values(Status),
    }
  })
  status: string;

  @property({
    type: 'object',
    jsonSchema: {
      type: "object",
      properties: {
        name: {
          type: "string",
        },
        updatedAt: {
          type: "string",
        },
        watchersCount: {
          type: "number"
        }
      },
      required: ['name', 'summary']
    }
  })
  repository?: object;

  @property({
    type: 'object',
    jsonSchema: {
      type: 'object',
      properties: {
        sha: {
          type: 'string'
        },
        repoName: {
          type: 'string'
        },
        author: {
          type: 'object',
          properties: {
            name: {
              type: 'string'
            },
            email: {
              type: 'string'
            },
            date: {
              type: 'string'
            },
          }
        },
        summary: {
          type: "object",
          properties: {
            readme: {
              type: "object",
              properties: {
                exists: {
                  type: "boolean",
                },
                title: {
                  type: "string"
                },
                status: {
                  type: "string"
                },
                useCases: {
                  type: "string"
                },
                studyType: {
                  type: "string"
                },
                tags: {
                  type: "string"
                },
                studyLead: {
                  type: "string"
                },
                startDate: {
                  type: "string"
                },
                endDate: {
                  type: "string"
                },
                protocol: {
                  type: "string"
                },
                publications: {
                  type: "string"
                },
                results: {
                  type: "string"
                },
              },
              required: ['exists']
            }
          },
          required: ['readme']
        }
      }
    }
  })
  readmeCommit?: object;

  @belongsTo(() => Scan)
  scanId: number;

  constructor(data?: Partial<ScanLog>) {
    super(data);
  }
}

export interface ScanLogRelations {
  // describe navigational properties here
}

export type ScanLogWithRelations = ScanLog & ScanLogRelations;
