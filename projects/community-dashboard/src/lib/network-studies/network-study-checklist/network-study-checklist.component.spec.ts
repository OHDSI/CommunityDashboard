import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NetworkStudyChecklistComponent } from './network-study-checklist.component';

describe('NetworkStudyChecklistComponent', () => {
  let component: NetworkStudyChecklistComponent;
  let fixture: ComponentFixture<NetworkStudyChecklistComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [NetworkStudyChecklistComponent]
    });
    fixture = TestBed.createComponent(NetworkStudyChecklistComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
