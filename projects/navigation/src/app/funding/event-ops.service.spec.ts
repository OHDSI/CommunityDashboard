import { TestBed } from '@angular/core/testing';

import { CfpOpsService } from './cfp-ops.service';

describe('EventOpsService', () => {
  let service: CfpOpsService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(CfpOpsService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
