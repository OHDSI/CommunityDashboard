import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StudyExplorerComponent } from './study-explorer.component';

describe('StudyExplorerComponent', () => {
  let component: StudyExplorerComponent;
  let fixture: ComponentFixture<StudyExplorerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ StudyExplorerComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(StudyExplorerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
