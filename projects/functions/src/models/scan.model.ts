import {Entity, model, property, hasMany} from '@loopback/repository';
import {ScanLog} from './scan-log.model';

@model()
export class Scan extends Entity {
  @property({
    type: 'number',
    id: true,
    generated: true,
  })
  id?: number;

  @property({
    type: 'string',
    required: true,
  })
  org: string;

  @hasMany(() => ScanLog)
  scanLogs: ScanLog[];

  constructor(data?: Partial<Scan>) {
    super(data);
  }
}

export interface ScanRelations {
  // describe navigational properties here
}

export type ScanWithRelations = Scan & ScanRelations;
