import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StudyLeadComponent } from './study-lead.component';

describe('StudyLeadComponent', () => {
  let component: StudyLeadComponent;
  let fixture: ComponentFixture<StudyLeadComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [StudyLeadComponent]
    });
    fixture = TestBed.createComponent(StudyLeadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
