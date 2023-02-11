import {inject, Getter} from '@loopback/core';
import {DefaultCrudRepository, repository, HasManyRepositoryFactory} from '@loopback/repository';
import {TestDataSource} from '../datasources';
import {Scan, ScanRelations, ScanLog} from '../models';
import {ScanLogRepository} from './scan-log.repository';

export class ScanRepository extends DefaultCrudRepository<
  Scan,
  typeof Scan.prototype.id,
  ScanRelations
> {

  public readonly scanLogs: HasManyRepositoryFactory<ScanLog, typeof Scan.prototype.id>;

  constructor(
    @inject('datasources.Test') dataSource: TestDataSource, @repository.getter('ScanLogRepository') protected scanLogRepositoryGetter: Getter<ScanLogRepository>,
  ) {
    super(Scan, dataSource);
    this.scanLogs = this.createHasManyRepositoryFactoryFor('scanLogs', scanLogRepositoryGetter,);
  }
}
