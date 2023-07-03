import { TestBed } from '@angular/core/testing';

import { OpenSourceEcosystemService } from './open-source-ecosystem.service';

describe('OpenSourceEcosystemService', () => {
  let service: OpenSourceEcosystemService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(OpenSourceEcosystemService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
