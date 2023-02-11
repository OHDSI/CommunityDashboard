import {inject, Getter} from '@loopback/core';
import {DefaultCrudRepository, repository, BelongsToAccessor} from '@loopback/repository';
import {TestDataSource} from '../datasources';
import {ScanLog, ScanLogRelations, Scan} from '../models';
import {ScanRepository} from './scan.repository';

export class ScanLogRepository extends DefaultCrudRepository<
  ScanLog,
  typeof ScanLog.prototype.id,
  ScanLogRelations
> {

  public readonly scan: BelongsToAccessor<Scan, typeof ScanLog.prototype.id>;

  constructor(
    @inject('datasources.Test') dataSource: TestDataSource, @repository.getter('ScanRepository') protected scanRepositoryGetter: Getter<ScanRepository>,
  ) {
    super(ScanLog, dataSource);
    this.scan = this.createBelongsToAccessorFor('scan', scanRepositoryGetter,);
    this.registerInclusionResolver('scan', this.scan.inclusionResolver);
  }
}
