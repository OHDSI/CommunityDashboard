import { TestBed } from '@angular/core/testing';

import { NetworkStudiesService } from './network-studies.service';

describe('NetworkStudiesService', () => {
  let service: NetworkStudiesService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(NetworkStudiesService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
