import { TestBed } from '@angular/core/testing';

import { NetworkStudyRepoService } from './network-study-repo.service';

describe('NetworkStudyRepoService', () => {
  let service: NetworkStudyRepoService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(NetworkStudyRepoService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
